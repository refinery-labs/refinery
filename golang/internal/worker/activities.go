package worker

import (
	"context"
	"log"

	"go.temporal.io/sdk/activity"

	"github.com/aws/aws-sdk-go/service/lambda"
	"github.com/aws/aws-sdk-go/service/sns"
	"github.com/aws/aws-sdk-go/service/sqs"
	"github.com/refinery-labs/refinery/golang/pkg/dsl"
)

type RefineryAwsActivities struct {
	ClientManager *AwsClientManager
}

func (a *RefineryAwsActivities) AwsLambdaActivity(ctx context.Context, params dsl.BlockActivityParams) (dsl.BlockResult, error) {
	var (
		resultData, backpackData, errorText string
	)

	lambdaClient, err := a.ClientManager.getLambdaClient(params.AccountID)
	if err != nil {
		activity.GetLogger(ctx).Error("error while getting lambda client", err)
		return dsl.BlockResult{}, err
	}

	lambdaInputData := getLambdaInputData(params.Data, params.Backpack)

	lambdaLogType := "Tail"
	invokeInput := &lambda.InvokeInput{
		FunctionName: &params.ResourceID,
		Payload:      lambdaInputData,
		LogType:      &lambdaLogType,
	}
	lambdaOutput, err := lambdaClient.Invoke(invokeInput)

	logResult := filterLogOutput(lambdaOutput.LogResult)

	if err != nil {
		a.writePipelineLogs(
			ctx,
			params,
			"EXCEPTION",
			logResult,
			resultData,
			backpackData,
		)
		return dsl.BlockResult{}, err
	}

	// If we are unable to unpack the response, fallback to
	resultData, backpackData, errorText, err = unpackLambdaResponse(lambdaOutput.Payload)
	if err != nil {
		log.Println("unable to unpack lambda response", string(lambdaOutput.Payload), err)
		resultData = string(lambdaOutput.Payload)
		backpackData = params.Backpack
	}

	a.writePipelineLogs(
		ctx,
		params,
		"SUCCESS",
		logResult,
		resultData,
		backpackData,
	)

	blockResult := dsl.BlockResult{
		Data:      resultData,
		Backpack:  backpackData,
		BlockType: dsl.AwsLambdaBlockType,
		IsError:   errorText != "",
	}

	if blockResult.IsError {
		blockResult.ErrorText = errorText
		// Fallback on the original backpack
		// TODO should the lambda return a backpack instead?
		blockResult.Backpack = params.Backpack
	}

	return blockResult, nil
}

func (a *RefineryAwsActivities) AwsPushToTopicActivity(ctx context.Context, params dsl.BlockActivityParams) (dsl.BlockResult, error) {
	snsClient, err := a.ClientManager.getSnsClient(params.AccountID)
	if err != nil {
		return dsl.BlockResult{}, err
	}

	snsInput := &sns.PublishInput{
		TopicArn: &params.ResourceID,
		Message:  &params.Data,
	}
	snsOutput, err := snsClient.Publish(snsInput)
	if err != nil {
		return dsl.BlockResult{}, err
	}

	result := dsl.BlockResult{
		Data:      *snsOutput.MessageId,
		Backpack:  params.Backpack,
		BlockType: dsl.AwsTopicBlockType,
	}
	return result, nil
}

func (a *RefineryAwsActivities) AwsPushToQueueActivity(ctx context.Context, params dsl.BlockActivityParams) (dsl.BlockResult, error) {
	sqsClient, err := a.ClientManager.getSqsClient(params.AccountID)
	if err != nil {
		return dsl.BlockResult{}, err
	}

	sqsInput := &sqs.SendMessageInput{
		QueueUrl:    &params.ResourceID,
		MessageBody: &params.Data,
	}
	sqsOutput, err := sqsClient.SendMessage(sqsInput)
	if err != nil {
		return dsl.BlockResult{}, err
	}

	result := dsl.BlockResult{
		Data:      *sqsOutput.MessageId,
		Backpack:  params.Backpack,
		BlockType: dsl.AwsQueueBlockType,
	}
	return result, nil
}
