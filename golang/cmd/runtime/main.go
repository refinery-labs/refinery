package main

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"regexp"
	"strings"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/refinery-labs/refinery/golang/internal/runtime"
)

const (
	OUTPUT_REGEX = `<REFINERY_OUTPUT_CUSTOM_RUNTIME>(.*)<\/REFINERY_OUTPUT_CUSTOM_RUNTIME>`
)

var (
	outputRegex = regexp.MustCompile(OUTPUT_REGEX)
)

func parseStdout(stdout string) (responseData runtime.HandlerResponse, err error) {
	output := outputRegex.FindStringSubmatch(stdout)
	if len(output) == 0 {
		err = fmt.Errorf("Unable to find output from handler")
		return
	}
	returnedData := output[1]
	err = json.Unmarshal([]byte(returnedData), &responseData)
	return
}

func HandleRequestApiGateway(ctx context.Context, request events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	var invokeEvent runtime.InvokeEvent

	err := json.Unmarshal([]byte(request.Body), &invokeEvent)
	if err != nil {
		return events.APIGatewayProxyResponse{}, err
	}

	resp, err := HandleRequest(invokeEvent)
	if err != nil {
		return events.APIGatewayProxyResponse{}, err
	}

	body, err := json.Marshal(resp)
	if err != nil {
		return events.APIGatewayProxyResponse{}, err
	}
	return events.APIGatewayProxyResponse{Body: string(body), StatusCode: 200}, nil
}

func HandleRequest(invokeEvent runtime.InvokeEvent) (lambdaResponse runtime.LambdaResponse, err error) {
	fmt.Printf("Handling request: %+v\n", invokeEvent)
	functionInput, err := json.Marshal(invokeEvent)
	if err != nil {
		return
	}

	handlerStdin := strings.NewReader(string(functionInput))

	cmd := runtime.ExecTask{
		Command: invokeEvent.Command,
		Args: []string{
			invokeEvent.Handler,
		},
		Cwd:         invokeEvent.Cwd,
		Stdin:       handlerStdin,
		StreamStdio: false,
	}

	res, err := cmd.Execute()

	fmt.Println("STDOUT", res.Stdout)
	fmt.Println("STDERR", res.Stderr)

	if err != nil {
		return
	}

	/*
		TODO should we use protobuf to communicate between the processes?
	*/
	handlerResponse, err := parseStdout(res.Stdout)
	if err != nil {
		return
	}

	if handlerResponse.Error != "" {
		err = fmt.Errorf("%s", handlerResponse.Error)
		return
	}

	lambdaResponse.Result = handlerResponse.Result
	lambdaResponse.Backpack = handlerResponse.Backpack
	return
}

func main() {
	fmt.Println("Starting runtime...")
	// Make the handler available for Remote Procedure Call by AWS Lambda
	lambdaEnv := os.Getenv("LAMBDA_ENVIRONMENT")
	switch lambdaEnv {
	case "API_GATEWAY":
		lambda.Start(HandleRequestApiGateway)
	default:
		lambda.Start(HandleRequest)
	}
}
