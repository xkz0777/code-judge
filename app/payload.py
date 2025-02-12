import uuid

from pydantic import BaseModel


class Submission(BaseModel):
    sub_id: str | None = None
    type: str  # `python`,`math`, ...
    options: dict[str, str]
    solution: str
    expected_answer: str

    def model_post_init(self, __context):
        self.sub_id = self.sub_id or str(uuid.uuid4())


class SubmissionResult(BaseModel):
    sub_id: str
    success: bool
    cost: float
