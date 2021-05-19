package main

import (
	"bytes"
	"encoding/base64"
	"errors"
	"io/ioutil"
	"log"
	"strings"

	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/ecr"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/google/go-containerregistry/pkg/authn"
	v1 "github.com/google/go-containerregistry/pkg/v1"
	"github.com/google/go-containerregistry/pkg/v1/tarball"
)

func getLayerFromS3(bucket, key string) (layer v1.Layer, err error) {
	sess, err := session.NewSession()
	if err != nil {
		log.Println(err)
		return
	}

	s3Client := s3.New(sess)
	input := s3.GetObjectInput{
		Bucket: aws.String(bucket),
		Key:    aws.String(key),
	}
	resp, err := s3Client.GetObject(&input)
	if err != nil {
		log.Println(err)
		return
	}
	defer resp.Body.Close()

	tarData, err := ioutil.ReadAll(resp.Body)
	if err != nil {
		log.Println(err)
		return
	}
	tarReader := bytes.NewReader(tarData)
	return tarball.LayerFromReader(tarReader)
}

func getAuthConfig(ecrClient *ecr.ECR) (authConfig authn.AuthConfig, err error) {
	log.Println("Getting authorization token from ecr...")
	ecrAuthToken, err := ecrClient.GetAuthorizationToken(nil)

	authData := ecrAuthToken.AuthorizationData
	if len(authData) == 0 {
		err = errors.New("No auth data for ecr")
		log.Println(err)
		return
	}

	authToken := *authData[0].AuthorizationToken

	auth, err := base64.StdEncoding.DecodeString(authToken)
	if err != nil {
		log.Println(err)
		return
	}

	authParts := strings.Split(string(auth), ":")

	authConfig = authn.AuthConfig{
		Username: authParts[0],
		Password: authParts[1],
	}
	return
}
