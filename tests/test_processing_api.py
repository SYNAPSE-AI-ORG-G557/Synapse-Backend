# In: Synapse-Backend/tests/test_processing_api.py

from fastapi.testclient import TestClient
from src.main import app  # Your FastAPI app instance

client = TestClient(app)

def test_create_processing_job_dispatches_task(mocker):
    """
    Tests that the /process endpoint returns 202 Accepted and calls
    the celery send_task function with the correct arguments.
    """
    # Mock the celery_app.send_task function
    mock_send_task = mocker.patch(
        "src.api.endpoints.processing.celery_app.send_task"
    )

    # Test payload for the API call
    test_payload = {"input_type": "text", "input_data": "Hello, world!"}

    # Make the API call to the /process endpoint
    response = client.post("/jobs/process", json=test_payload)

    # Assert the HTTP status code is 202 Accepted
    assert response.status_code == 202

    # Assert the response JSON contains a job_id
    response_json = response.json()
    assert "job_id" in response_json

    # Assert celery_app.send_task was called exactly once
    mock_send_task.assert_called_once()

    # Inspect the arguments used in the send_task call
    call_args, call_kwargs = mock_send_task.call_args

    # The first positional argument is the task name (string)
    task_name = call_args[0]

    # 'args' is passed as a keyword argument, so get it from call_kwargs
    task_args = call_kwargs.get("args")

    assert task_name == "src.tasks.cpu_light_tasks.route_input_task"
    assert isinstance(task_args, list)
    assert isinstance(task_args[0], str)  # job_id as a string
    assert task_args[1] == test_payload   # The job_in data matches test payload
