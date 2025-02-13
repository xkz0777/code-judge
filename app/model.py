import uuid

from pydantic import BaseModel


class Submission(BaseModel):
    sub_id: str | None = None
    type: str  # `python`,`math`, ...
    options: dict[str, str] | None = None
    solution: str
    input: str | None = None
    expected_output: str

    def model_post_init(self, __context):
        self.sub_id = self.sub_id or str(uuid.uuid4())


class WorkPayload(BaseModel):
    work_id: str | None = None
    submission: Submission

    def model_post_init(self, __context):
        self.work_id = self.work_id or str(uuid.uuid4())


class SubmissionResult(BaseModel):
    sub_id: str
    success: bool
    cost: float
