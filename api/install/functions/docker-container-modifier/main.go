package main

import (
	"bytes"
	"encoding/base64"
	"fmt"
	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/ecr"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/google/go-containerregistry/pkg/authn"
	"github.com/google/go-containerregistry/pkg/crane"
	v1 "github.com/google/go-containerregistry/pkg/v1"
	"github.com/google/go-containerregistry/pkg/v1/tarball"
	"io/ioutil"
	"log"
	"os"
	"strings"
)

type ImageFile struct {
	Bucket     string `json:"bucket"`
	Key string `json:"key"`
}

type InvokeEvent struct {
	Registry     string      `json:"registry"`
	BaseImage    string      `json:"base_image"`
	NewImageName string      `json:"new_image_name"`
	ImageFiles   ImageFile `json:"image_files"`
}

type InvokeResponse struct {
	Tag string `json:"tag"`
	DeploymentID string `json:"deployment_id"`
	WorkDir string `json:"work_dir"`
}

func ApiGatewayHandler(request events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	fmt.Println("Received body: ", request.Body)

	return events.APIGatewayProxyResponse{Body: request.Body, StatusCode: 200}, nil
}

func getLayerFromS3(bucket, key string) (layer v1.Layer, err error) {
	sess, err := session.NewSession()
	if err != nil {
		return
	}

	s3Client := s3.New(sess)
	input := s3.GetObjectInput{
		Bucket:                     aws.String(bucket),
		Key:                        aws.String(key),
	}
	resp, err := s3Client.GetObject(&input)
	if err != nil {
		return
	}
	defer resp.Body.Close()

	tarData, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		return
	}
	tarReader := bytes.NewReader(tarData)
	return tarball.LayerFromReader(tarReader)
}

func Handler(invokeEvent InvokeEvent) (resp InvokeResponse, err error) {
	sess, err := session.NewSession(&aws.Config{
		Region: aws.String("us-west-2"),
	})

	if err != nil {
		return
	}

	ecrClient := ecr.New(sess)

	log.Println("Getting authorization token from ecr...")
	ecrAuthToken, err := ecrClient.GetAuthorizationToken(nil)

	authData := ecrAuthToken.AuthorizationData
	if len(authData) == 0 {
		return resp, fmt.Errorf("No auth data for ecr")
	}

	authToken := *authData[0].AuthorizationToken

	auth, err := base64.StdEncoding.DecodeString(authToken)
	if err != nil {
		return
	}

	authParts := strings.Split(string(auth), ":")

	cfg := authn.AuthConfig{
		Username: authParts[0],
		Password: authParts[1],
	}

	authenticator := authn.FromConfig(cfg)

	options := crane.WithAuth(authenticator)

	refineryRuntimeRepo := os.Getenv("REFINERY_CONTAINER_RUNTIME_REPOSITORY")
	log.Println("Pulling Refinery container runtime from:", refineryRuntimeRepo)

	runtimeImage, err := crane.Pull(refineryRuntimeRepo)
	if err != nil {
		return
	}

	log.Println("Creating function files layer...")
	functionFilesLayer, err := getLayerFromS3(invokeEvent.ImageFiles.Bucket, invokeEvent.ImageFiles.Key)
	if err != nil {
		return
	}


	log.Println("Getting runtime image layers...")
	runtimeLayers, err := runtimeImage.Layers()
	if err != nil {
		return
	}

	appendLayers := append(runtimeLayers, functionFilesLayer)

	newTag := fmt.Sprintf("%s/%s", invokeEvent.Registry, invokeEvent.NewImageName)

	log.Println("Modifying docker image...")
	containerConfig, err := ModifyDockerBaseImage(invokeEvent.BaseImage, newTag, appendLayers, options)
	if err != nil {
		return
	}

	return InvokeResponse{
		Tag:          containerConfig.tag,
		DeploymentID: containerConfig.deploymentID,
		WorkDir: containerConfig.workDir,
	}, nil
}

func main() {
	lambda.Start(Handler)
}
