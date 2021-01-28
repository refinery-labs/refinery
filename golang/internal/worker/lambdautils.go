package worker

import (
	"bufio"
	"bytes"
	"context"
	"encoding/base64"
	"encoding/json"
	"fmt"
	"regexp"
	"strings"
	"time"

	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/google/uuid"
	"github.com/refinery-labs/refinery/golang/pkg/dsl"
	"go.temporal.io/sdk/activity"
)

func getNowInUTC() time.Time {
	return time.Now().UTC()
}

func getNearestFiveMinutes() time.Time {
	dt := getNowInUTC()
	return dt.Truncate(5 * time.Minute)
}

func (s *RefineryAwsActivities) writePipelineLogs(
	ctx context.Context,
	params dsl.BlockActivityParams,
	logType,
	programOutput,
	returnData,
	backpack string,
) error {
	logID := uuid.New()

	dateShardString := "dt=" + getNearestFiveMinutes().Format("2006-01-02-15-04")

	currentTime := getNowInUTC().Unix()

	arnParts := strings.Split(params.ResourceID, ":")
	lambdaName := arnParts[len(arnParts)-1]

	workflowRunID := activity.GetInfo(ctx).WorkflowExecution.RunID

	s3Path := fmt.Sprintf(
		"%s/%s/%s/%s~%s~%s~%d",
		params.ProjectID, dateShardString, workflowRunID, logType, lambdaName, logID, currentTime)

	s3Data := map[string]string{
		"id":                    logID.String(),
		"execution_pipeline_id": workflowRunID,
		"project_id":            params.ProjectID,
		"arn":                   params.ResourceID,
		"function_name":         lambdaName,
		"name":                  lambdaName,
		"type":                  logType, // INPUT, EXCEPTION, SUCCESS
		"timestamp":             fmt.Sprintf("%d", currentTime),
		"program_output":        programOutput,
		"backpack":              backpack,
		"input_data":            params.Data,
		"return_data":           returnData,
	}

	s3Client, err := s.ClientManager.getS3Client(params.AccountID)
	if err != nil {
		return err
	}

	serializedData, err := json.Marshal(s3Data)
	if err != nil {
		return err
	}

	buf := bytes.NewReader(serializedData)

	input := s3.PutObjectInput{
		Bucket: &params.S3LogBucket,
		Key:    &s3Path,
		Body:   buf,
	}

	_, err = s3Client.PutObject(&input)
	return err
}

type LambdaResponsePayload struct {
	ErrorType    string   `json:"errorType"`
	ErrorMessage string   `json:"errorMessage"`
	ErrorTrace   []string `json:"trace"`
	Result       string   `json:"result"`
	Backpack     string   `json:"backpack"`
}

func unpackLambdaResponse(lambdaResponsePayload []byte) (lambdaResponse LambdaResponsePayload, err error) {
	var unpackedString string
	err = json.Unmarshal(lambdaResponsePayload, &unpackedString)
	if err != nil {
		unpackedString = string(lambdaResponsePayload)
	}

	err = json.Unmarshal([]byte(unpackedString), &lambdaResponse)
	if err != nil {
		return
	}

	if lambdaResponse.ErrorMessage == "" {
		lambdaResponse.ErrorMessage = "{}"
	}

	if len(lambdaResponse.Result) == 0 {
		lambdaResponse.Result = "{}"
	}

	if len(lambdaResponse.Backpack) == 0 {
		lambdaResponse.Backpack = "{}"
	}
	return
}

const logMetaRegex = `^(START RequestId: |END RequestId: |REPORT RequestId: |XRAY TraceId: )`

func filterLogOutput(logResult *string) string {
	if logResult == nil {
		return ""
	}

	logResultBytes, err := base64.StdEncoding.DecodeString(*logResult)
	if err != nil {
		return ""
	}

	re := regexp.MustCompile(logMetaRegex)

	bufferStr := bytes.NewBufferString("")
	scanner := bufio.NewScanner(strings.NewReader(string(logResultBytes)))
	for scanner.Scan() {
		line := scanner.Text()
		if re.MatchString(line) {
			continue
		}
		bufferStr.WriteString(line + "\n")
	}
	return bufferStr.String()
}

func getLambdaInputData(data, backpack string) []byte {
	// TODO figure out how to properly format this data
	// (it is challenging because there are different formats and whatnot)
	if backpack == "" {
		backpack = "{}"
	}
	return []byte(fmt.Sprintf("{\"block_input\": %s, \"backpack\": %s}", data, backpack))
}
