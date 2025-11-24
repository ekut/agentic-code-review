import os
from crewai import Agent, Crew, Process, Task
from crewai.project import CrewBase, agent, crew, task
from crewai_tools import (
	SerperDevTool,
    ScrapeWebsiteTool,
)
from pydantic import BaseModel
from agentic_code_review.utils import (
    get_serper_api_key, 
    get_openai_api_key,
    get_senior_developer_model,
    get_security_engineer_model,
    get_tech_lead_model
)
# import the guardrails
from agentic_code_review.crews.code_review_crew.guardrails.guardrails import security_review_output_guardrail

os.environ["OPENAI_API_KEY"] = get_openai_api_key()
os.environ["SERPER_API_KEY"] = get_serper_api_key()

@CrewBase
class CodeReviewCrew:
    """CodeReview crew"""
    @agent
    def senior_developer(self) -> Agent:
        model = get_senior_developer_model()
        agent_config = {
            "config": self.agents_config["senior_developer"],
        }
        if model:
            agent_config["llm"] = model
        return Agent(**agent_config)

    @agent
    def security_engineer(self) -> Agent:
        os.environ["SERPER_API_KEY"] = get_serper_api_key()
        
        # Get base_url from environment or use default
        base_url = os.getenv("DLAI_SERPER_BASE_URL", "https://google.serper.dev")
        
        model = get_security_engineer_model()
        agent_config = {
            "config": self.agents_config["security_engineer"],
            "tools": [
                # add the SerperDevTool to the agent's tools
                SerperDevTool(search_url="https://owasp.org",
                              base_url=base_url),
                ScrapeWebsiteTool() 
            ],
        }
        if model:
            agent_config["llm"] = model
        return Agent(**agent_config)
    
    @agent
    def tech_lead(self) -> Agent:
        model = get_tech_lead_model()
        agent_config = {
            "config": self.agents_config["tech_lead"],
        }
        if model:
            agent_config["llm"] = model
        return Agent(**agent_config)
        
    @task
    def analyze_code_quality(self) -> Task:
        # Define the pydantic model for the code quality analysis output
        class CodeQualityJSON(BaseModel):
            critical_issues: list[str]
            minor_issues: list[str]
            reasoning: str
        return Task(
            config=self.tasks_config["analyze_code_quality"],
            output_json=CodeQualityJSON,
            
            # allow for asynchronous execution
            async_execution=True,
        )
    
    @task
    def review_security(self) -> Task:
        # Define the pydantic model for the security vulnerabilities
        class SecurityVulnerability(BaseModel):
            description: str 
            risk_level: str 
            evidence: str

        # Define the pydantic model for the security review output
        class ReviewSecurityJSON(BaseModel):
            security_vulnerabilities: list[SecurityVulnerability] 
            blocking: bool
            highest_risk: str
            security_recommendations: list[str]

        return Task(
            config=self.tasks_config["review_security"],
            output_json=ReviewSecurityJSON,

            # allow for asynchronous execution
            async_execution=True,

            # add the security review output guardrail (already imported above)
            guardrails=[security_review_output_guardrail]
        )
    
    @task
    def summarize_findings(self) -> Task:
        
        # Define the pydantic model for the fixes output
        class Fix(BaseModel):
            description: str 
            solutions: str 
            explanation: str

        # Define the pydantic model for the summarized findings output
        class SummarizedFindingsJSON(BaseModel):
            confidence: int
            findings: str
            fix: list[Fix]
            recommendations: list[str]
        
        return Task(
            config=self.tasks_config["summarize_findings"],
            # Set the Markdown parameter to get the final report in Markdown format
            output_json=SummarizedFindingsJSON,
        )
    

    @crew
    def crew(self) -> Crew:
        """Creates the CodeReviewCrew crew"""
        from crewai.memory import ShortTermMemory, EntityMemory
        
        return Crew(
            agents=self.agents,  # Automatically created by the @agent decorator
            tasks=self.tasks,  # Automatically created by the @task decorator
            # set the process to sequential
            process=Process.sequential,
            verbose=True,
            memory=False,
            # Disabled due to tools[0].name error with instructor+litellm
            # memory=True,
            # short_term_memory=ShortTermMemory(),
            # entity_memory=EntityMemory(),
            # long_term_memory=None,  
        )