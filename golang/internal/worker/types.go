package worker

import (
	"github.com/aws/aws-sdk-go/service/lambda"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/aws/aws-sdk-go/service/sns"
	"github.com/aws/aws-sdk-go/service/sqs"
)

type WorkerConfig struct {
	Region             string `yaml:"region"`
	ClientDuration     int64  `yaml:"client_duration"`
	IAMRoleName        string `yaml:"iam_role_name"`
	AwsAccessKeyID     string `yaml:"aws_access_key_id"`
	AwsSecretAccessKey string `yaml:"aws_secret_access_key"`
	TemporalHostPort   string `yaml:"temporal_host_port"`
}

type AwsClients struct {
	LambdaClient *lambda.Lambda
	SnsClient    *sns.SNS
	SqsClient    *sqs.SQS
	S3Client     *s3.S3
}
