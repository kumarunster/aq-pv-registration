import pytest
from mongomock_motor import AsyncMongoMockClient


@pytest.fixture
def mongomock_motor_db():
    #['test']
    return AsyncMongoMockClient()['test_netzanmeldung']
