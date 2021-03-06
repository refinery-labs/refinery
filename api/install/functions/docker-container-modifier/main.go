package main

import (
	"archive/tar"
	"bytes"
	"encoding/base64"
	"fmt"
	"log"
	"os"
	"sort"
	"strings"

	"github.com/aws/aws-lambda-go/events"
	"github.com/aws/aws-lambda-go/lambda"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/ecr"
	"github.com/google/go-containerregistry/pkg/authn"
	"github.com/google/go-containerregistry/pkg/crane"
	v1 "github.com/google/go-containerregistry/pkg/v1"
	"github.com/google/go-containerregistry/pkg/v1/tarball"
)

var (
	EFS_PATH = "/mnt/efs"
)

type ImageFile struct {
	Path     string `json:"path"`
	Contents string `json:"contents"`
}

type InvokeEvent struct {
	Registry     string      `json:"registry"`
	BaseImage    string      `json:"base_image"`
	NewImageName string      `json:"new_image_name"`
	ImageFiles   []ImageFile `json:"image_files"`
}

type InvokeResponse struct {
	Success bool `json:"success"`
}

func ApiGatewayHandler(request events.APIGatewayProxyRequest) (events.APIGatewayProxyResponse, error) {
	fmt.Println("Received body: ", request.Body)

	return events.APIGatewayProxyResponse{Body: request.Body, StatusCode: 200}, nil
}

// Layer creates a layer from a single file map. These layers are reproducible and consistent.
// A filemap is a path -> file content map representing a file system.
func Layer(filemap map[string][]byte) (v1.Layer, error) {
	b := &bytes.Buffer{}
	w := tar.NewWriter(b)

	fn := []string{}
	for f := range filemap {
		fn = append(fn, f)
	}
	sort.Strings(fn)

	for _, f := range fn {
		c := filemap[f]
		if err := w.WriteHeader(&tar.Header{
			Name: f,
			Size: int64(len(c)),
			Mode: 0o755,
		}); err != nil {
			return nil, err
		}
		if _, err := w.Write(c); err != nil {
			return nil, err
		}
	}
	if err := w.Close(); err != nil {
		return nil, err
	}
	return tarball.LayerFromReader(b)
}

func Handler(invokeEvent InvokeEvent) (hashLookup map[string]string, err error) {
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
		return hashLookup, fmt.Errorf("No auth data for ecr")
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

	filemap := map[string][]byte{}
	for _, imageFile := range invokeEvent.ImageFiles {
		contents, nerr := base64.StdEncoding.DecodeString(imageFile.Contents)
		if nerr != nil {
			return
		}
		filemap[imageFile.Path] = contents
	}

	log.Println("Creating function files layer...")
	functionFilesLayer, err := Layer(filemap)
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
	hash, err := ModifyDockerBaseImage(invokeEvent.BaseImage, newTag, appendLayers, options)

	return map[string]string{
		invokeEvent.NewImageName: hash,
	}, err
}

func main() {
	lambda.Start(Handler)
}
