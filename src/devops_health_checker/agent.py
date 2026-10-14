from devops_health_checker.workflow import (
    DevOpsWorkflow,
    SYSTEM_PROMPT,
)


class DevOpsAgent:
    def __init__(
        self,
        registry,
        llm_client=None,
        max_iterations: int = 5,
    ):
        self.registry = registry

        self.workflow = DevOpsWorkflow(
            registry=registry,
            llm_client=llm_client,
            max_iterations=max_iterations,
        )
        self.llm = self.workflow.llm
        self.max_iterations = self.workflow.max_iterations
        self.tools = self.workflow.tools

    def run(
        self,
        user_message: str,
    ) -> str:
        return self.workflow.run(user_message)
