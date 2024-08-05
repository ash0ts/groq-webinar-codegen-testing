from pydantic import BaseModel, Field


class EvaluationCriterion(BaseModel):
    """
    Represents a single evaluation criterion for code review.

    This model defines the structure for evaluating a specific aspect of code,
    including a numerical score and a textual explanation.

    Attributes:
        score (int): A numerical score between 1 and 10.
        explanation (str): A brief explanation justifying the given score.
    """

    score: int = Field(
        ...,
        ge=1,
        le=10,
        description="A numerical score between 1 and 10 for the evaluation criterion"
    )
    explanation: str = Field(
        ...,
        description="A brief explanation justifying the given score"
    )


class CodeEvaluation(BaseModel):
    """
    Represents a comprehensive evaluation of generated code.

    This model includes evaluations for various aspects of code quality,
    as well as an overall assessment.

    Attributes:
        correctness (EvaluationCriterion): Evaluation of the code's correctness.
        efficiency (EvaluationCriterion): Evaluation of the code's efficiency.
        readability (EvaluationCriterion): Evaluation of the code's readability.
        error_handling (EvaluationCriterion): Evaluation of the code's error handling.
        overall (EvaluationCriterion): Overall evaluation of the code.
    """

    correctness: EvaluationCriterion = Field(
        ...,
        description="Evaluation of whether the code correctly implements the requested functionality"
    )
    efficiency: EvaluationCriterion = Field(
        ...,
        description="Evaluation of whether the code is implemented efficiently"
    )
    readability: EvaluationCriterion = Field(
        ...,
        description="Evaluation of whether the code is easy to read and understand"
    )
    error_handling: EvaluationCriterion = Field(
        ...,
        description="Evaluation of whether the code handles potential errors appropriately"
    )
    overall: EvaluationCriterion = Field(
        ...,
        description="Overall evaluation of the code, considering all criteria"
    )
