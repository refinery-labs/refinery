package runtime

/*
func successResponse(body ResponseData) HandlerResponse {
	serializedBody, err := json.Marshal(body)
	if err != nil {
		return HandlerResponse{
			StatusCode: 400,
			Headers: map[string]string{
				"Content-Type":                "application/json",
				"Access-Control-Allow-Origin": "*",
			},
			Body: err.Error(),
		}
	}

	return HandlerResponse{
		StatusCode: 200,
		Headers: map[string]string{
			"Content-Type":                "application/json",
			"Access-Control-Allow-Origin": "*",
		},
		Body: string(serializedBody),
	}
}

func errorResponse(err error) HandlerResponse {
	fmt.Println(err.Error())

	body := ResponseData{
		Error: err.Error(),
	}

	serializedBody, err := json.Marshal(body)
	if err != nil {
		return HandlerResponse{
			StatusCode: 400,
			Headers: map[string]string{
				"Content-Type":                "application/json",
				"Access-Control-Allow-Origin": "*",
			},
			Body: err.Error(),
		}
	}

	return HandlerResponse{
		StatusCode: 400,
		Headers: map[string]string{
			"Content-Type":                "application/json",
			"Access-Control-Allow-Origin": "*",
		},
		Body: string(serializedBody),
	}
}
*/
