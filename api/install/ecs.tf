//resource "aws_ecs_cluster" "refinery_builders_cluster" {
//  name = "refinery_builders"
//}
//
//data "aws_ecs_task_definition" "refinery_builders_task_definition" {
//  task_definition = "${aws_ecs_task_definition.refinery_builders_task_definition.family}"
//  depends_on = [ "aws_ecs_task_definition.refinery_builders_task_definition" ]
//}
//
//# Set up CloudWatch group and log stream and retain logs for 30 days
//resource "aws_cloudwatch_log_group" "refinery_builders_log_group" {
//  name              = "/ecs/refinery-builders"
//  retention_in_days = 7
//
//  tags = {
//    RefineryResource = "true"
//  }
//}
//
//resource "aws_cloudwatch_log_stream" "cb_log_stream" {
//  name           = "refinery-builders"
//  log_group_name = aws_cloudwatch_log_group.refinery_builders_log_group.name
//}
//
//# ECS task execution role data
//data "aws_iam_policy_document" "ecs_task_execution_role" {
//  version = "2012-10-17"
//  statement {
//    sid = ""
//    effect = "Allow"
//    actions = ["sts:AssumeRole"]
//
//    principals {
//      type        = "Service"
//      identifiers = ["ecs-tasks.amazonaws.com"]
//    }
//  }
//}
//
//# ECS task execution role
//resource "aws_iam_role" "ecs_task_execution_role" {
//  name               = "RefineryBuilderECSExecutionRole"
//  assume_role_policy = data.aws_iam_policy_document.ecs_task_execution_role.json
//}
//
//# ECS task execution role policy attachment
//resource "aws_iam_role_policy_attachment" "ecs_task_execution_role" {
//  role       = aws_iam_role.ecs_task_execution_role.name
//  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
//}
//
///*
//  Firewall rules for the launched tasks
//*/
//resource "aws_security_group" "refinery_builders_security_group" {
//  name        = "refinery_builders_security_group"
//  description = "The security group for Refinerys builder instances."
//
//  /*
//      Allow inbound TCP on port 2222
//  */
//  ingress {
//    from_port   = 2222
//    to_port     = 2222
//    protocol    = "tcp"
//    cidr_blocks = ["0.0.0.0/0"]
//  }
//
//  # Allow all outbound
//  egress {
//    from_port   = 0
//    to_port     = 0
//    protocol    = "-1"
//    cidr_blocks = ["0.0.0.0/0"]
//  }
//}
//
//resource "aws_ecs_task_definition" "refinery_builders_task_definition" {
//  family                   = "refinery_builders_task_family"
//
//  requires_compatibilities = ["FARGATE"]
//  network_mode             = "awsvpc"
//  cpu                      = "2048"
//  memory                   = "4096"
//  execution_role_arn       = aws_iam_role.ecs_task_execution_role.arn
//
//  container_definitions    = <<DEFINITION
//[
//  {
//      "environment": [],
//      "name": "refinery-builders",
//      "mountPoints": [],
//      "image": "refinerylabs/refinery-builders:latest",
//      "cpu": 0,
//      "memoryReservation": null,
//      "portMappings": [
//          {
//              "protocol": "tcp",
//              "containerPort": 2222,
//              "hostPort": 2222
//          }
//      ],
//      "logConfiguration": {
//          "logDriver": "awslogs",
//          "options": {
//              "awslogs-region": "${var.region}",
//              "awslogs-stream-prefix": "ecs",
//              "awslogs-group": "/ecs/refinery-builders"
//          }
//      },
//      "essential": true,
//      "volumesFrom": []
//  }
//]
//DEFINITION
//}
//
//resource "aws_default_subnet" "default_az1" {
//  availability_zone = "us-west-2a"
//}
//
//resource "aws_ecs_service" "refinery_builders_service" {
//  name            = "refinery_builders"
//  cluster         = aws_ecs_cluster.refinery_builders_cluster.id
//  desired_count   = 0
//  launch_type     = "FARGATE"
//  task_definition = "${aws_ecs_task_definition.refinery_builders_task_definition.family}:${max("${aws_ecs_task_definition.refinery_builders_task_definition.revision}", "${data.aws_ecs_task_definition.refinery_builders_task_definition.revision}")}"
//
//  network_configuration {
//    security_groups  = [aws_security_group.refinery_builders_security_group.id]
//    subnets          = aws_default_subnet.default_az1.*.id
//    assign_public_ip = true
//  }
//}