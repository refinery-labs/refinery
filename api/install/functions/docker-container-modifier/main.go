package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"os"
	"path"
	"path/filepath"
	"strings"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	v1 "github.com/google/go-containerregistry/pkg/v1"
	"github.com/google/go-containerregistry/pkg/v1/tarball"
)

// TODO: These are duplicated from the Loq golang monorepo, we should probably put this service there at some point.
const FunctionsPath = `/var/runtime/functions.json`

type RefineryFunction struct {
	Command      string            `json:"command"`
	Handler      string            `json:"handler"`
	ImportPath   string            `json:"import_path"`
	FunctionName string            `json:"function_name"`
	WorkDir      string            `json:"work_dir"`
	Env          map[string]string `json:"env"`
}

func ApiGatewayHandler(request events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	fmt.Println("Received body: ", request.Body)

	return events.APIGatewayProxyResponse{Body: request.Body, StatusCode: 200}, nil
}

func isLocalDev() bool {
	return len(os.Args) != 1
}

func Handler(invokeEvent InvokeEvent) (resp InvokeResponse, err error) {
	options, err := loadCraneOptions()
	if err != nil {
		return
	}

	log.Println("Creating function files layer...")
	functionFilesLayer, err := getLayerFromS3(invokeEvent.ImageFiles.Bucket, invokeEvent.ImageFiles.Key)
	if err != nil {
		return
	}

	runtimeLayers, err := loadRuntimeLayers()
	if err != nil {
		return
	}

	appendLayers := []v1.Layer{functionFilesLayer}
	if invokeEvent.ModifyEntrypoint {
		appendLayers = append(appendLayers, runtimeLayers...)
	}

	newTag := fmt.Sprintf("%s/%s", invokeEvent.Registry, invokeEvent.NewImageName)

	modifier := NewDockerContainerModifier(
		invokeEvent.BaseImage,
		false,
		invokeEvent.ModifyEntrypoint,
		options,
	)

	base, err := modifier.LoadImage()
	if err != nil {
		log.Println(err)
		return
	}

	log.Println("Modifying docker image...")
	newImg, containerConfig, err := modifier.AppendLayersToBaseImage(base, appendLayers)
	if err != nil {
		return
	}

	modifier.PushImage(newImg, newTag)

	return InvokeResponse{
		Tag:          containerConfig.tag,
		DeploymentID: containerConfig.deploymentID,
		WorkDir:      containerConfig.workDir,
	}, nil
}

func loadFunctionConfig(functionsConfigFile string) (configFile FunctionConfigFile, err error) {
	data, err := ioutil.ReadFile(functionsConfigFile)
	if err != nil {
		log.Println(err)
		return
	}

	err = json.Unmarshal(data, &configFile)
	if err != nil {
		log.Println(err)
		return
	}
	return
}

func getNewContainerNames(containerTarFile string) (newTag, newFilename string) {
	basename := path.Base(containerTarFile)
	basenameExt := filepath.Ext(basename)
	tag := strings.TrimSuffix(basename, basenameExt)

	newTag = fmt.Sprintf("lunasec-%s", tag)
	newFilename = newTag + basenameExt
	return
}

func modifyDevelopmentContainer(containerTarFile, functionsConfigFile string) {
	configFile, err := loadFunctionConfig(functionsConfigFile)
	if err != nil {
		panic(err)
	}

	modifier := NewDockerContainerModifier(
		containerTarFile,
		true,
		true,
		nil,
	)

	base, err := modifier.LoadImage()
	if err != nil {
		log.Println(err)
		return
	}

	imgConfigFile, err := base.ConfigFile()
	if err != nil {
		log.Println(err)
		return
	}

	workDir := imgConfigFile.Config.WorkingDir

	var refineryFunctions []RefineryFunction
	for _, f := range configFile.Functions {
		// TODO (cthompson) hardcoded for testing, most of the logic for building the function config is in python
		// we should move the logic into this code since it makes more sense to have it here for testing locally.
		refineryFunction := RefineryFunction{
			Command:      "node",
			Handler:      "container_lambda_function.js",
			ImportPath:   f.ImportPath,
			FunctionName: f.FunctionName,
			WorkDir:      workDir,
			// TODO (cthompson) we need to get env variables into this function from the user
			Env: map[string]string{},
		}
		refineryFunctions = append(refineryFunctions, refineryFunction)
	}

	functionData, err := json.Marshal(refineryFunctions)
	if err != nil {
		log.Println(err)
		return
	}

	files := []InMemoryFile{
		{FunctionsPath, string(functionData)},
	}

	tarData, err := buildInMemoryTarFile(files)
	if err != nil {
		log.Println(err)
		return
	}
	fileLayer, err := tarball.LayerFromReader(&tarData)
	if err != nil {
		log.Println(err)
		return
	}

	runtimeLayers, err := loadRuntimeLayersFromTar()
	if err != nil {
		log.Println(err)
		return
	}

	appendLayers := []v1.Layer{
		fileLayer,
	}
	appendLayers = append(appendLayers, runtimeLayers...)

	img, _, err := modifier.AppendLayersToBaseImage(base, appendLayers)
	if err != nil {
		log.Println(err)
		return
	}

	newTag, newFilename := getNewContainerNames(containerTarFile)

	log.Printf("saving modified container image to: %s\n", newFilename)
	err = modifier.SaveImageToFile(img, newTag, newFilename)
	if err != nil {
		log.Println(err)
		return
	}
}

func main() {
	log.SetFlags(log.Lshortfile)

	// TODO (cthompson) we should control building this code with tags https://stackoverflow.com/questions/38950909/c-style-conditional-compilation-in-golang
	localDev := isLocalDev()
	if !localDev {
		lambda.Start(Handler)
	}

	if len(os.Args) != 3 {
		log.Printf("usage: %s <container tar file> <lunasec config file>", os.Args[0])
		return
	}

	containerTarFile := os.Args[1]
	functionsConfigFile := os.Args[2]
	modifyDevelopmentContainer(containerTarFile, functionsConfigFile)
}
