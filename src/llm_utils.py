from typing import Optional, Any, Dict
from groq import Groq
import instructor
import os
import config
import weave


@weave.op()
def generate_with_retry(
    model_name: str,
    messages: list,
    response_model: Any,
    use_seed: bool = True,
    seed: Optional[int] = None,
    **kwargs
) -> Any:
    client: instructor.Instructor = instructor.from_groq(
        Groq(api_key=os.getenv("GROQ_API_KEY")), mode=instructor.Mode.TOOLS)

    if use_seed:
        seeds = [seed] if seed is not None else config.SEEDS
        print(f"Using seeds: {seeds}")
        for current_seed in seeds:
            try:
                return attempt_with_seed(client, model_name, messages, response_model, current_seed, **kwargs)
            except Exception as e:
                print(f"Attempt with seed {current_seed} failed: {str(e)}")
                if current_seed == seeds[-1]:
                    raise Exception("All seed attempts failed")
    else:
        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            response_model=response_model,
            max_retries=config.MAX_RETRIES,
            **kwargs
        )
        return response


@weave.op()
def attempt_with_seed(
    client: instructor.Instructor,
    model_name: str,
    messages: list,
    response_model: Any,
    seed: int,
    **kwargs
) -> Any:
    return client.chat.completions.create(
        model=model_name,
        messages=messages,
        response_model=response_model,
        seed=seed,
        max_retries=3,
        **kwargs
    )
