# pipeline.py
from typing import TypedDict, Literal, Optional
from langgraph.graph import StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_groq import ChatGroq

# Define the input/output state structure
class UnifiedState(TypedDict, total=False):
    mode: Literal["generate", "improve"]
    task_description: str
    context: Optional[str]
    base_template: Optional[str]
    prompt: Optional[str]
    feedback: Optional[str]
    score: Optional[float]
    issue_found: Optional[bool]
    improved_prompt: Optional[str]

# Main pipeline builder
def build_pipeline(groq_api_key: str):
    groq_llm = ChatGroq(groq_api_key=groq_api_key, model="llama-3.1-8b-instant", temperature=0)

    # Define LangGraph node functions
    def dispatcher_node(state: UnifiedState) -> dict:
        return {}

    def dispatcher_router(state: UnifiedState) -> str:
        return "PromptImproverDirect" if state.get("mode") == "improve" else "ContextBuilder"

    def context_builder(state: UnifiedState) -> dict:
        return {"context": f"You are a helpful assistant. Task: {state['task_description']}"}

    def template_selector(state: UnifiedState) -> dict:
        return {"base_template": "Given the following task, create a useful prompt: {task_description}"}

    def prompt_generator(state: UnifiedState) -> dict:
        input_text = state["base_template"].format(task_description=state["task_description"])
        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are an expert prompt engineer."),
            ("human", input_text)
        ])
        response = (prompt | groq_llm).invoke({})
        return {"prompt": response.content}

    def prompt_evaluator(state: UnifiedState) -> dict:
        eval_input = f"Evaluate this prompt: '{state['prompt']}'. Return only a float score between 0.0 and 1.0"
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Respond with only a float."),
            ("human", eval_input)
        ])
        response = (prompt | groq_llm).invoke({})
        try:
            score = float(''.join(c for c in response.content if c.isdigit() or c == '.'))
        except:
            score = 0.5
        return {"score": score, "issue_found": score < 0.7}

    def critique_node(state: UnifiedState) -> dict:
        critique_prompt = f"Critique and suggest improvements: {state['prompt']}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Be a constructive prompt critic."),
            ("human", critique_prompt)
        ])
        response = (prompt | groq_llm).invoke({})
        return {"feedback": response.content}

    def loop_improver(state: UnifiedState) -> dict:
        improve_input = f"Feedback: {state['feedback']}\nPrompt: {state['prompt']}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Improve this prompt based on feedback."),
            ("human", improve_input)
        ])
        response = (prompt | groq_llm).invoke({})
        return {"prompt": response.content}

    def prompt_improver_direct(state: UnifiedState) -> dict:
        improve_input = f"Prompt: {state['prompt']}\nContext: {state['context']}"
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Improve this prompt with the given context."),
            ("human", improve_input)
        ])
        response = (prompt | groq_llm).invoke({})
        return {"improved_prompt": response.content}

    # Build the graph
    workflow = StateGraph(UnifiedState)
    workflow.add_node("Dispatcher", dispatcher_node)
    workflow.add_node("ContextBuilder", context_builder)
    workflow.add_node("PromptTemplateSelector", template_selector)
    workflow.add_node("PromptGenerator", prompt_generator)
    workflow.add_node("PromptEvaluator", prompt_evaluator)
    workflow.add_node("CritiqueNode", critique_node)
    workflow.add_node("LoopImproverAgent", loop_improver)
    workflow.add_node("PromptImproverDirect", prompt_improver_direct)

    workflow.set_entry_point("Dispatcher")

    workflow.add_conditional_edges("Dispatcher", dispatcher_router, {
        "PromptImproverDirect": "PromptImproverDirect",
        "ContextBuilder": "ContextBuilder"
    })

    workflow.add_edge("ContextBuilder", "PromptTemplateSelector")
    workflow.add_edge("PromptTemplateSelector", "PromptGenerator")
    workflow.add_edge("PromptGenerator", "PromptEvaluator")

    def eval_router(state: UnifiedState) -> str:
        return "critique_and_improve" if state.get("issue_found") else END

    workflow.add_conditional_edges("PromptEvaluator", eval_router, {
        "critique_and_improve": "CritiqueNode",
        END: END
    })

    workflow.add_edge("CritiqueNode", "LoopImproverAgent")
    workflow.add_edge("LoopImproverAgent", "PromptEvaluator")
    workflow.add_edge("PromptImproverDirect", END)

    return workflow.compile()
