package main

import (
	"context"
	"encoding/json"
	"errors"
	"fmt"
	"go.uber.org/zap"
	"io/ioutil"
	"log"
	"os"
	"regexp"
	"strings"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/refinery-labs/refinery/golang/internal/runtime"
)

var (
	outputRegex = regexp.MustCompile(runtime.OutputRegexStr)
)

func parseStdout(stdout string) (responseData runtime.HandlerResponse, err error) {
	output := outputRegex.FindStringSubmatch(stdout)
	if len(output) == 0 {
		err = fmt.Errorf("unable to find output from handler")
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

func loadFunctionLookup() (functionLookup runtime.FunctionLookup, err error) {
	var data []byte

	functionLookup = runtime.FunctionLookup{}

	data, err = ioutil.ReadFile(runtime.FunctionsPath)
	if err != nil {
		fmt.Println("File reading error", err)
		return
	}

	err = json.Unmarshal(data, &functionLookup)
	if err != nil {
		fmt.Println("Error parsing rpc function lookup", err)
		return
	}
	return functionLookup, err
}

func getFunctionConfig(functionName string) (funcConfig runtime.RefineryFunction, err error) {
	var (
		ok bool
		functionLookup runtime.FunctionLookup
	)

	functionLookup, err = loadFunctionLookup()
	if err != nil {
		return
	}

	if functionName == "" {
		functionName = os.Getenv("REFINERY_FUNCTION_NAME")
	}

	funcConfig, ok = functionLookup[functionName]
	if !ok {
		err = fmt.Errorf("unable to find function with name: %s", functionName)
	}
	return
}

func HandleRequest(invokeEvent runtime.InvokeEvent) (lambdaResponse runtime.LambdaResponse, err error) {
	var (
		functionInput []byte
		funcConfig runtime.RefineryFunction
		res runtime.ExecResult
		handlerResponse runtime.HandlerResponse
	)

	logger, err := zap.NewDevelopment()
	if err != nil {
		log.Println("unable to create zap logger", err)
		return
	}

	logger.Debug(
		"handling request:",
		zap.String("request", fmt.Sprintf("%+v", invokeEvent)),
	)

	funcConfig, err = getFunctionConfig(invokeEvent.FunctionName)
	if err != nil {
		logger.Error(
			"unable to get function config",
			zap.Error(err),
		)
		return
	}

	req := runtime.InvokeFunctionRequest{
		BlockInput:   invokeEvent.BlockInput,
		Backpack:     invokeEvent.Backpack,
		ImportPath:   funcConfig.ImportPath,
		FunctionName: funcConfig.FunctionName,
	}

	functionInput, err = json.Marshal(req)
	if err != nil {
		logger.Error(
			"unable to marshal function request",
			zap.Error(err),
		)
		return
	}

	envVars := os.Environ()

	for k, v := range funcConfig.Env {
		envVars = append(envVars, k + "=" + v)
	}

	handlerStdin := strings.NewReader(string(functionInput))

	refineryCommand := runtime.ExecTask{
		Command: funcConfig.Command,
		Args: []string{
			funcConfig.Handler,
		},
		Env: 		 envVars,
		Cwd:         funcConfig.WorkDir,
		Stdin:       handlerStdin,
		StreamStdio: false,
	}

	res, err = refineryCommand.Execute()
	if err != nil {
		logger.Error(
			"error when executing handler command",
			zap.Error(err),
		)
		return
	}

	logger.Debug("handler stdout", zap.String("stdout", res.Stdout))
	logger.Debug("handler stderr", zap.String("stderr", res.Stderr))

	/*
		TODO should we use protobuf to communicate between the processes?
	*/
	handlerResponse, err = parseStdout(res.Stdout)
	if err != nil {
		logger.Error("error while parsing stdout from handler", zap.Error(err))
		return
	}

	logger.Debug(
		"handler response",
		zap.String(
			"handlerResponse",
			fmt.Sprintf("%v", handlerResponse),
		),
	)

	if handlerResponse.Error != "" {
		err = errors.New(handlerResponse.Error)
		logger.Error("handler error", zap.Error(err))
		return
	}

	lambdaResponse.Result = handlerResponse.Result
	lambdaResponse.Backpack = handlerResponse.Backpack
	return
}

func main() {
	fmt.Println("Starting runtime...")

	// Make the handler available for Remote Procedure Call by AWS Lambda
	lambdaEnv := os.Getenv("LAMBDA_CALLER")
	switch lambdaEnv {
	case "API_GATEWAY":
		lambda.Start(HandleRequestApiGateway)
	default:
		lambda.Start(HandleRequest)
	}
}
