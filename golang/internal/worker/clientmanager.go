package worker

import (
	"fmt"
	"log"
	"sync"
	"time"

	"github.com/ReneKroon/ttlcache/v2"
	"github.com/aws/aws-sdk-go/aws"
	"github.com/aws/aws-sdk-go/aws/credentials"
	"github.com/aws/aws-sdk-go/aws/session"
	"github.com/aws/aws-sdk-go/service/lambda"
	"github.com/aws/aws-sdk-go/service/s3"
	"github.com/aws/aws-sdk-go/service/sns"
	"github.com/aws/aws-sdk-go/service/sqs"
	"github.com/aws/aws-sdk-go/service/sts"
	"github.com/google/uuid"
)

type (
	NewClientFunc func(*session.Session) interface{}
)

type AwsClientType string

const (
	LambdaClientType AwsClientType = "lambda"
	S3ClientType     AwsClientType = "s3"
	SNSClientType    AwsClientType = "sns"
	SQSClientType    AwsClientType = "sqs"
)

func newLambdaClient(sess *session.Session) interface{} {
	return lambda.New(sess)
}

func newS3Client(sess *session.Session) interface{} {
	return s3.New(sess)
}
func newSNSClient(sess *session.Session) interface{} {
	return sns.New(sess)
}
func newSQSClient(sess *session.Session) interface{} {
	return sqs.New(sess)
}

type AwsClientManager struct {
	region                 string
	clientDuration         int64
	iamRoleName            string
	stsClient              *sts.STS
	clientCache            *ttlcache.Cache
	clientMutexLookup      map[string]*sync.Mutex
	clientMutexLookupMutex sync.Mutex
}

func NewAwsClientManager(workflowManagerConfig WorkerConfig) *AwsClientManager {
	awsAccessKeyID := workflowManagerConfig.AwsAccessKeyID
	awsSecretAccessKey := workflowManagerConfig.AwsSecretAccessKey
	region := workflowManagerConfig.Region
	clientDuration := workflowManagerConfig.ClientDuration
	iamRoleName := workflowManagerConfig.IAMRoleName

	credentials := credentials.NewStaticCredentials(
		awsAccessKeyID,
		awsSecretAccessKey,
		"",
	)

	sess, err := session.NewSession(&aws.Config{
		Region:      aws.String(region),
		Credentials: credentials,
	})
	if err != nil {
		log.Fatalln("Unable to create session", err)
	}

	stsClient := sts.New(sess)

	clientCacheTTL := (time.Duration(clientDuration) * time.Second) - (time.Duration(10) * time.Minute)

	clientCache := ttlcache.NewCache()
	clientCache.SetTTL(clientCacheTTL)

	return &AwsClientManager{
		region:            region,
		iamRoleName:       iamRoleName,
		stsClient:         stsClient,
		clientCache:       clientCache,
		clientMutexLookup: map[string]*sync.Mutex{},
	}
}

func (m *AwsClientManager) cleanup() {
	m.clientCache.Close()
}

func (m *AwsClientManager) getSession(accountID string) (*session.Session, error) {
	roleArn := fmt.Sprintf("arn:aws:iam::%s:role/%s", accountID, m.iamRoleName)
	roleSessionName := fmt.Sprintf("%s-%s", accountID, uuid.New().String())
	duration := int64(900)
	input := &sts.AssumeRoleInput{
		RoleArn:         &roleArn,
		RoleSessionName: &roleSessionName,
		DurationSeconds: &duration,
	}
	output, err := m.stsClient.AssumeRole(input)
	if err != nil {
		return nil, err
	}

	credentials := credentials.NewStaticCredentials(
		*output.Credentials.AccessKeyId,
		*output.Credentials.SecretAccessKey,
		*output.Credentials.SessionToken,
	)

	return session.NewSession(&aws.Config{
		Region:      aws.String(m.region),
		Credentials: credentials,
	})
}

func (m *AwsClientManager) getMutexForClient(cacheKey string) *sync.Mutex {
	// is this overkill? seems necessary...
	m.clientMutexLookupMutex.Lock()
	defer m.clientMutexLookupMutex.Unlock()

	clientMutex, ok := m.clientMutexLookup[cacheKey]
	if !ok {
		clientMutex = &sync.Mutex{}
		m.clientMutexLookup[cacheKey] = clientMutex
	}
	return clientMutex
}

func (m *AwsClientManager) getClientFromCache(clientType AwsClientType, newClientFunc NewClientFunc, accountID string) (interface{}, error) {
	cacheKey := string(clientType) + accountID + m.region
	if value, err := m.clientCache.Get(cacheKey); err == nil {
		return value, nil
	}

	clientMutex := m.getMutexForClient(cacheKey)
	clientMutex.Lock()
	defer clientMutex.Unlock()

	sess, err := m.getSession(accountID)
	if err != nil {
		return nil, err
	}

	newClient := newClientFunc(sess)
	m.clientCache.Set(cacheKey, newClient)
	return newClient, nil
}

func (m *AwsClientManager) getLambdaClient(accountID string) (*lambda.Lambda, error) {
	sess, err := m.getSession(accountID)

	if err != nil {
		return nil, err
	}

	return newLambdaClient(sess).(*lambda.Lambda), nil
}

func (m *AwsClientManager) getS3Client(accountID string) (*s3.S3, error) {
	client, err := m.getClientFromCache(S3ClientType, newS3Client, accountID)
	if err != nil {
		return nil, err
	}

	s3Client, ok := client.(*s3.S3)
	if !ok {
		return nil, fmt.Errorf("unable to type assert client: %v", client)
	}
	return s3Client, nil
}

func (m *AwsClientManager) getSnsClient(accountID string) (*sns.SNS, error) {
	client, err := m.getClientFromCache(SNSClientType, newSNSClient, accountID)
	if err != nil {
		return nil, err
	}

	snsClient, ok := client.(*sns.SNS)
	if !ok {
		return nil, fmt.Errorf("unable to type assert client: %v", client)
	}
	return snsClient, nil
}

func (m *AwsClientManager) getSqsClient(accountID string) (*sqs.SQS, error) {
	client, err := m.getClientFromCache(SQSClientType, newSQSClient, accountID)
	if err != nil {
		return nil, err
	}

	sqsClient, ok := client.(*sqs.SQS)
	if !ok {
		return nil, fmt.Errorf("unable to type assert client: %v", client)
	}
	return sqsClient, nil
}
