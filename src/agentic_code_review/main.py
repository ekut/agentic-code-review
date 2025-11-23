from pydantic import BaseModel
from pathlib import Path
from crewai import LLM
from crewai.flow import Flow, listen, start, router, or_, persist
# from typing import Literal, Optional
from agentic_code_review.crews.code_review_crew.crew import CodeReviewCrew
from agentic_code_review.providers import ProviderFactory
from agentic_code_review.utils import get_github_token
import dill
import json

import os
os.environ["CREWAI_TESTING"] = "true"
PROJECT_ROOT = Path(__file__).parent.parent.parent

# define the flow state
class ReviewState(BaseModel):
    # Input configuration (simplified - provider-agnostic)
    pr_input: str = str(PROJECT_ROOT / "files" / "code_changes.txt")  # Can be file path, GitHub URL, etc.
    
    # PR data
    pr_content: str = "" # initialize with an empty string
    pr_metadata: dict = {} # PR metadata (title, description, author, files_changed, url, provider)
    
    # Existing fields
    errors: list = [] # initialize with an empty list
    review_result: dict = {} # set the correct type
    crew_needed: bool = False # set the correct type
    tokens_used: dict = {} # initialize with an empty dict
    final_answer: str = "" # initialize with an empty string


@persist()
# Define the flow
class PRCodeReviewFlow(Flow[ReviewState]):
    """
    CrewAI Flow for automated code review of pull requests.
    """
    @start()
    def read_pr_data(self):
        """
        Read PR data using appropriate provider (file, GitHub, etc.).
        Provider is automatically detected based on input format.
        """
        print("🔍 Starting PR Code Review...")
        
        # Get the input from the state
        pr_input = self.state.pr_input

        if not pr_input:
            # append some error message to the errors state variable
            self.state.errors.append("Missing 'pr_input' in state") 
            # save the error message in the final answer state variable
            self.state.final_answer = "No input provided. Please set 'pr_input' with a file path or PR URL."
            print(f"❌ {self.state.final_answer}")
            return

        # try fetching PR data using the provider factory
        try:
            # Get appropriate provider (factory pattern)
            provider = ProviderFactory.get_provider(
                pr_input,
                github_token=get_github_token()
                # Future: gitlab_token=..., bitbucket_token=...
            )
            
            # Fetch PR data (unified interface)
            # Pass both url and file_path to support different providers
            pr_data = provider.fetch_pr_data(url=pr_input, file_path=pr_input)
            
            # Update state with unified data
            self.state.pr_content = pr_data.diff
            self.state.pr_metadata = {
                "title": pr_data.title,
                "description": pr_data.description,
                "author": pr_data.author,
                "files_changed": pr_data.files_changed,
                "url": pr_data.url,
                "provider": pr_data.provider,
                "pr_number": pr_data.pr_number,
                "repository": pr_data.repository,
            }
               
        # if there are any issues, raise an error
        except Exception as e:
            error_message = f"Error fetching PR data: {str(e)}"
            print(f"❌ {error_message}")
            # append some error message to the errors state variable
            self.state.errors.append("Error fetching PR data")
            # save the error message in the final answer state variable
            self.state.final_answer = error_message


    @router("read_pr_data")
    def analyze_changes(self, context):
        """Route to appropriate review type based on complexity"""

        # if there are any errors in the state variable, return 'ERROR'
        if len(self.state.errors) > 0:
            return 'ERROR'

        else:
            # define the prompt to analyze the changes
            prompt = (
                "Analyze this pull request diff file and respond with exactly one word: SIMPLE or COMPLEX.\n"
                "SIMPLE: small changes that don't compromise code quality or security. For example typos, minor refactoring, formatting, small doc changes"
                "COMPLEX: bigger changes that need closer inspection. For example new features, bug fixes, logic changes, security-relevant changes, or anything requiring deep review or best practices research.\n"
                f"\nPR Diff:\n{self.state.pr_content}\n"
                )

            # define the llm for the decision 
            llm = LLM(model="gpt-4o-mini",) 
            # call the llm and save the result
            decision = llm.call(messages=prompt) 
            
            # the word COMPLEX is in the decision, 
            # set the crew_needed to True in the state and return "COMPLEX"
            if "COMPLEX" in decision.upper():
                ### START CODE HERE ###
                self.state.crew_needed = True
                return 'COMPLEX'
            # if not COMPLEX (i.e. SIMPLE)
            # set the crew_needed to False in the state and return "SIMPLE"
            else:
                self.state.crew_needed = False
                return 'SIMPLE'

    # if the PR is simple, do a simple review
    @listen('SIMPLE')
    def simple_review(self):
        """Simple review for minor changes"""
        print("⚡ Performing simple review...")
        
        # Complete the last part of the prompt
        prompt = (
            "Analyze this pull request diff file and evaluate the changes.\n"
            "Do not make assumptions or considerations about the code outside of the diff provided, but if warranted you can make suggestions.\n"
            "Decide whether the changes are good to be accepted or if other measures are needed")

        # define the llm for the decision 
        llm = LLM(model="gpt-4o-mini",)
        # call the llm and save the result
        result = llm.call(messages=prompt)

        # Save the result of the LLM call in the review_result state variable
        self.state.review_result = result
    

    # if the PR is complex, deploy crew review
    @listen('COMPLEX')
    def full_crew_review(self):
        """Full crew review for complex changes"""
        print("🚀 Starting full crew review...")
        
        # get the PR content from the state variable
        pr_content = self.state.pr_content

        # create the crew
        code_review_crew = CodeReviewCrew().crew()

        try: 
            # kickoff the crew. Pass the PR content in the inputs
            result = code_review_crew.kickoff(inputs={'file_content': pr_content})

            # save the results in the state variable. You can use the `json_dict` attribute of the result
            self.state.review_result = result.json_dict

            # save the tokens used by the crew. You can use the `token_usage` attribute of the result
            self.state.tokens_used = result.token_usage
        except Exception as e:
            error_message = f"There was an error during the crew review: \n{str(e)}"
            print(f"❌ {error_message}")
            # append some error message to the errors state variable
            self.state.errors.append("Error during crew review")
            # save the error message in the final answer state variable
            self.state.final_answer = error_message

    # make the final decision based on the review results
    @listen(or_(simple_review, full_crew_review))
    def make_final_decision(self):
        """Make the final decision based on the review results"""
        print("🧐 Making final decision based on review results...")
        
        # get the review result from the state variable
        review_result = self.state.review_result

        # use an LLM call to make the final decision and generate the final message
        prompt = (
            "Based on the following analysis of the pull request diff file, "
            "make a final decision on whether to approve the PR for merging.\n" \
            "Any review with a confidence score above 85 can be approves, but improvements can be suggested.\n"
            "Return a full report with:\n"
            "- Final Review Decision: APPROVE (the PR is good to be approved), REQUEST CHANGES (the PR needs some modifications, but they are concrete changes) " 
            " or ESCALATE (the PR requires human attention, there are major issues that need fixing)\n"
            "- Confidence Score: int. A confidence score between 0-100 that indicates the confidence for merging the PR\n"
            "- Findings: str. A summary of the key findings\n"
            "- If the decision is to REQUEST CHANGES, provide a list of the changes requested to grant approval\n"
            "- If the decision is to ESCALATE, provide a list of reasons why the PR needs to be escalated to a human reviewer, along with possible solutions\n"
            f"\nAnalysis:\n{review_result}\n"
        )
        llm = LLM(model="gpt-4o-mini",)
        
        # make the LLM call
        final_decision = llm.call(messages=prompt)
        # save the final answer in the state variable
        self.state.final_answer = final_decision


    # return the final answer
    @listen(or_("ERROR", "make_final_decision"))
    def return_final_answer(self):
        """Return the final answer to the user"""

        print("📝 Final Answer:")
        print(f"{self.state.final_answer}")
        print("\n✨ Automatic code review completed!")
        return self.state.final_answer


def kickoff():
    import sys
    import argparse
    
    # Parse CLI arguments
    parser = argparse.ArgumentParser(description='Run PR code review flow')
    parser.add_argument('--input-source', type=str, help='PR input source (file path or GitHub URL)')
    args = parser.parse_args()
    
    # Prepare inputs
    inputs = {"id": "my_code_review_flow"}
    if args.input_source:
        inputs["pr_input"] = args.input_source
    
    # instantiate the flow with tracing enabled
    pr_code_review_flow = PRCodeReviewFlow(tracing=True)
    # kickoff the flow. 
    # Here you have a custom id set so that that you can use the persistence features
    result = pr_code_review_flow.kickoff(inputs=inputs)

    # save the result of the flow - for grading purposes
    with open('../result.dill', 'wb') as f:
        dill.dump(result, f)
    # Save the flow state as JSON - for grading purposes
    with open('../flow_state.json', 'w') as f:
        json.dump(pr_code_review_flow.state.model_dump(), f, indent=2)


def plot():
    pr_code_review_flow = PRCodeReviewFlow()
    pr_code_review_flow.plot()


if __name__ == "__main__":
    kickoff()
