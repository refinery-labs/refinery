package main

import (
	"context"
	"encoding/json"
	"fmt"
	"io/ioutil"
	"os"
	"path"
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

func getFunctionConfig(functionName string) (functionName_ string, funcConfig runtime.RefineryFunction, err error) {
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

	functionName_ = functionName

	funcConfig, ok = functionLookup[functionName]
	if !ok {
		err = fmt.Errorf("unable to find function with name: %s", functionName)
	}
	return
}

func HandleRequest(invokeEvent runtime.InvokeEvent) (lambdaResponse runtime.LambdaResponse, err error) {
	var (
		functionName string
		functionInput []byte
		funcConfig runtime.RefineryFunction
		res runtime.ExecResult
		handlerResponse runtime.HandlerResponse
	)

	fmt.Printf("Handling request: %+v\n", invokeEvent)

	functionName, funcConfig, err = getFunctionConfig(invokeEvent.FunctionName)
	if err != nil {
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
		return
	}

	cwd := path.Join(runtime.RuntimeDir, functionName)
	if invokeEvent.WorkDir != "" {
		cwd = invokeEvent.WorkDir
	}

	handlerStdin := strings.NewReader(string(functionInput))

	refineryCommand := runtime.ExecTask{
		Command: funcConfig.Command,
		Args: []string{
			funcConfig.Handler,
		},
		Cwd:         cwd,
		Stdin:       handlerStdin,
		StreamStdio: false,
	}

	res, err = refineryCommand.Execute()

	if err != nil {
		fmt.Printf("%s\n", err)
		return
	}

	/*
		TODO should we use protobuf to communicate between the processes?
	*/
	handlerResponse, err = parseStdout(res.Stdout)
	if err != nil {
		fmt.Println(res.Stdout)
		fmt.Println(res.Stderr)
		fmt.Printf("%s\n", err)
		return
	}

	fmt.Println(handlerResponse)

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
