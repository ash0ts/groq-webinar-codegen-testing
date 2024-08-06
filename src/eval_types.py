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

    This model includes evaluations for key aspects of code generation quality
    based on academic research.

    Attributes:
        functional_correctness (EvaluationCriterion): Evaluation of whether the code correctly solves the intended problem.
        code_quality (EvaluationCriterion): Evaluation of code readability, efficiency, and adherence to best practices.
        generalization (EvaluationCriterion): Evaluation of performance across different languages, tasks, and complexity levels.
        consistency (EvaluationCriterion): Evaluation of output consistency for similar inputs.
        error_handling (EvaluationCriterion): Evaluation of how well the code handles potential errors and edge cases.
        overall (EvaluationCriterion): Overall evaluation of the code, considering all criteria.
    """

    functional_correctness: EvaluationCriterion = Field(
        ...,
        description="Evaluation of whether the code correctly solves the intended problem"
    )
    code_quality: EvaluationCriterion = Field(
        ...,
        description="Evaluation of code readability, efficiency, and adherence to best practices"
    )
    generalization: EvaluationCriterion = Field(
        ...,
        description="Evaluation of performance across different languages, tasks, and complexity levels"
    )
    consistency: EvaluationCriterion = Field(
        ...,
        description="Evaluation of output consistency for similar inputs"
    )
    error_handling: EvaluationCriterion = Field(
        ...,
        description="Evaluation of how well the code handles potential errors and edge cases"
    )
    overall: EvaluationCriterion = Field(
        ...,
        description="Overall evaluation of the code, considering all criteria"
    )
