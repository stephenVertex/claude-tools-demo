from time import time
from typing import Dict, List, Any, Optional, Tuple
from typing_extensions import Annotated
from pydantic import BaseModel, Field, ValidationError

################################################################################
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.text import Text
from rich.style import Style
from rich.theme import Theme

################################################################################

import json
import boto3
import clickuphelper as ch
import requests
from datetime import datetime, timedelta
import pytz
from secrets_manager import get_secret
import dateparser
import os
import uuid
import pickle
import yaml

from TaskModels import *
from sbctutil import *

from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown


from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit import prompt
from prompt_toolkit.keys import Keys
from prompt_toolkit.filters import Condition
from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import ANSI, HTML
from prompt_toolkit.styles import Style

console = Console()

## GET SECRETS. You are going to need to fill these in from the environment or
## from a secrets manager. The dtype variable allows me to have a "demo" environment
## and a "work" environment which reference separate OKRs and ClickUp Lists
secret            = get_secret("prod/sjbClickUp")  ## This accesses the secret local to the account
cu_token          = secret["CLICKUP_API_KEY"]
headers           = {"Authorization": cu_token}
cu_team_id        = secret["CLICKUP_TEAM_ID"]
dtype             = os.environ["DTYPE"]
list_name_key     = "CLICKUP_LIST_" + dtype.upper() + "_NAME"
list_id_key       = "CLICKUP_LIST_" + dtype.upper()
CU_LIST_NAME      = secret[list_name_key]
CU_LIST_ID        = secret[list_id_key]
WORKFLOWY_API_KEY = secret["WORKFLOWY_API_KEY"]  ## Not used in this demo


# CONFIGURE CLICKUP HELPER MODULE
ch.team_id        = cu_team_id
ch.headers        = headers


# HELPERS
def dt_validate(tu_input: TaskUpdate) -> Tuple[TaskUpdate, Dict[str, str]]:
    errors = {}

    if tu_input.due_date and not tu_input.due_date_millis:
        parsed_due_date = dateparser.parse(tu_input.due_date)
        if parsed_due_date:
            tu_input.due_date_millis = int(parsed_due_date.timestamp() * 1000)
        else:
            errors["due_date"] = "Failed to parse due_date"

    if tu_input.start_date and not tu_input.start_date_millis:
        parsed_start_date = dateparser.parse(tu_input.start_date)
        if parsed_start_date:
            tu_input.start_date_millis = int(parsed_start_date.timestamp() * 1000)
        else:
            errors["start_date"] = "Failed to parse start_date"

    print("Successfully validated input: " + str(tu_input))

    return tu_input, errors


def tx_to_Task(tx: ch.Task) -> Task:
    date_fields = ["date_created", "date_done", "date_closed", "due_date", "start_date"]
    time_qty_fields = ["time_estimate"]
    
    task_dict = {
        "name": tx.name,
        # "id": tx.id, ## TODO this might come back to bite me. Keep an eye here.
        "id" : tx.task["id"],
        "priority": tx.task["priority"],
        "status": tx.status,
        "description": tx.task["description"],
        "tags": [x["name"] for x in tx.task["tags"]]
    }
    
    for field in date_fields:
        if field in tx.task:
            task_dict[field] = (
                None if tx.task[field] is None
                else convert_unix_to_iso8601_pacific(tx.task[field])
            )
    
    for field in time_qty_fields:
        if field in tx.task:
            task_dict[field] = (
                None if tx.task[field] is None
                else milliseconds_to_hh_mm_ss(tx.task[field])
            )
    
    return Task(**task_dict)

# CORE FUNCTIONALITY
# - Add tags to task
# - Update task 
# - Create task
# - Add comment to task
# - Set task to completed
# - Get tasks due this week
# - Get a specific task by ID
# - List tasks by tag
# - Get current datetime
# - Load OKRs into context
# - Get all tasks in list
def add_tags_to_task_core(task_tags: TaskTags) -> TaskUpdateModel:
    tx = ch.Task(task_tags.task_id)
    for tag_id in task_tags.tag_ids:
        url = f"https://api.clickup.com/api/v2/task/{task_tags.task_id}/tag/{tag_id}"
        response = requests.post(url, headers=ch.headers)
    return TaskUpdateModel(task_id=task_tags.task_id, updated=True)


def update_task_core(task_update: TaskUpdate) -> TaskUpdateModel:
    url = f"https://api.clickup.com/api/v2/task/{task_update.task_id}"
    task_update, dt_errors = dt_validate(task_update)
    payload = task_update.dict(exclude_unset=True, exclude={'task_id'})    
    if task_update.due_date_millis:
        payload["due_date"] = task_update.due_date_millis
        del payload["due_date_millis"]
    if task_update.start_date_millis:
        payload["start_date"] = task_update.start_date_millis
        del payload["start_date_millis"]
    print(f"Calling clickup with payload: {payload}")
    resp = requests.put(url, json=payload, headers=ch.headers)
    return TaskUpdateModel(task_id=task_update.task_id, updated=resp.status_code == 200)

def create_task_core(task_create: TaskCreate) -> TaskUpdateModel:
    tx = ch.post_task(CU_LIST_ID, task_create.task_name, task_create.task_description)
    response_json = tx.json()
    return TaskUpdateModel(task_id=response_json.get('id'), updated=True)

def add_comment_to_task_core(task_comment: TaskAddComment) -> TaskUpdateModel:
    tx = ch.Task(task_comment.task_id)
    x = tx.post_comment(task_comment.comment)
    return TaskUpdateModel(task_id=task_comment.task_id, updated=True)


def set_task_to_completed_core(task_id: TaskIdModel) -> TaskUpdateModel:
    tx = ch.Task(task_id.task_id)
    tx.post_status("completed")
    return TaskUpdateModel(task_id=task_id.task_id, updated=True)

def get_week_to_date_tasks_core(input_params: WeekToDateTasksInput) -> TaskList:
    ## This should use server side filtering.
    ## Look at sjbutil.get_episode_shorts for how to do this.
    ## This should be done with sjbutil.
    print(f"Getting tasks from: {CU_LIST_NAME}")
    admin_tasks = ch.get_list_tasks("DevGraph", None, CU_LIST_NAME)
    simple_tasks_list = []
    date_sunday_lb = get_most_recent_sunday_as_timestamp()
    
    for t_id, tx in admin_tasks.tasks.items():
        if input_params.skip_past_due:
            due_date = tx.task.get("due_date")
            if due_date is None or date_sunday_lb > int(due_date):
                print(f"{tx.name} is past due or due date is not set. Skipping")
                continue
        
        if tx.status in ['completed', 'cancelled']:
            continue
        
        task = tx_to_Task(tx)
        simple_tasks_list.append(task)
    
    for st in simple_tasks_list:
        print(f"{st.name} - {st.due_date}")
    
    return TaskList(
        task_list=simple_tasks_list,
        current_datetime=datetime.now(pytz.timezone('US/Pacific'))
    )

def get_specific_task(task_id: TaskIdModel) -> Task:
    tx = ch.Task(task_id.task_id)
    return tx_to_Task(tx)


 
def list_tasks_by_tags(tag_id_list: TagIdList) -> TaskList:
    """
    Query tasks from a ClickUp list, filtered by tag IDs.

    Args:
    api_token (str): Your ClickUp API token.
    list_id (str): The ID of the list to query tasks from.
    tag_id_list (TagIdList): A Pydantic model containing a list of tag IDs to filter the tasks by.

    Returns:
    TaskList: A Pydantic model containing a list of Task objects.
    
    Raises:
    requests.RequestException: If there's an error with the API request.
    ValueError: If the API response indicates an error.
    """
    base_url = f'https://api.clickup.com/api/v2/list/{CU_LIST_ID}/task'
    
    headers = ch.headers    
    params = {
        'tags[]': tag_id_list.tag_ids,
        'subtasks': 'true',  # Include subtasks in the response
        'include_closed': 'true'  # Include closed tasks
    }
    
    try:
        response = requests.get(base_url, headers=headers, params=params)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        data = response.json()
        
        if 'err' in data:
            raise ValueError(f"API Error: {data['err']}")
        
        # Convert the API response to our Pydantic model
        tasks = []
        for task_data in data['tasks']:
            tx = ch.Task(task_data['id'])
            task_model = tx_to_Task(tx)
            tasks.append(task_model)

        return TaskList(task_list=tasks,
                        current_datetime=datetime.now(pytz.timezone('US/Pacific')))
    
    except requests.RequestException as e:
        raise requests.RequestException(f"Error making request to ClickUp API: {str(e)}")


def get_current_datetime(NullModel) -> CurrentDateTime:
    return CurrentDateTime(current_datetime=datetime.now(pytz.timezone('US/Pacific')))
    

def load_okrs_into_context(NullModel) -> OKRSet:
    # Get the DTYPE from environment variable, defaulting to an empty string if not set
    dtype = os.environ.get('DTYPE', '')

    # Choose the file based on DTYPE
    if dtype.lower() == 'demo':
        filename = "okr-michael-scott.demo.yaml"
    else:
        filename = "okr-stephen-barr-2024-q3.yaml"

    # Attempt to load the YAML file
    try:
        with open(filename, 'r') as file:
            yaml_data = yaml.safe_load(file)
    except FileNotFoundError:
        print(f"Error: The file {filename} was not found.")
        return None
    except yaml.YAMLError as e:
        print(f"Error parsing the YAML file: {e}")
        return None

    # Assuming OKRSet is a class that can be instantiated with a dictionary
    return OKRSet(**yaml_data)


# https://app.clickup.com/6914877/v/l/6-182675650-1
def get_all_tasks(NullModel) -> TaskList:
    all_tasks_tx = ch.get_list_tasks("DevGraph", None, "Administrative")
    tlist = []
    for task_id, task in all_tasks_tx.tasks.items():
        tm = tx_to_Task(task)
        tlist.append(tm)
    return TaskList(
        task_list=tlist,
        current_datetime=datetime.now(pytz.timezone('US/Pacific'))
    )

    
################################################################################
## Creating a set of tool schemas so I can use it for an agent

function_io_map = {
    "add_tags_to_task_core": {
        "input": TaskTags,
        "output": TaskUpdateModel,
        "description": "Adds specified tags to a task",
        "function": add_tags_to_task_core
    },
    "update_task_core": {
        "input": TaskUpdate,
        "output": TaskUpdateModel,
        "description": "Updates a task with the provided information",
        "function": update_task_core
    },
    "create_task_core": {
        "input": TaskCreate,
        "output": TaskUpdateModel,
        "description": "Creates a new task with the given name and description",
        "function": create_task_core
    },
    "add_comment_to_task_core": {
        "input": TaskAddComment,
        "output": TaskUpdateModel,
        "description": "Adds a comment to a specified task",
        "function": add_comment_to_task_core
    },
    "set_task_to_completed_core": {
        "input": TaskIdModel,
        "output": TaskUpdateModel,
        "description": "Marks a task as completed",
        "function": set_task_to_completed_core
    },
    "get_week_to_date_tasks_core": {
        "input": WeekToDateTasksInput,
        "output": TaskList,
        "description": "Retrieves tasks due in the current week",
        "function": get_week_to_date_tasks_core
    },
    "get_specific_task": {
        "input": TaskIdModel,
        "output": Task,
        "description": "Get a particular task by ID",
        "function": get_specific_task
    },
    "list_tasks_by_tag" : {
        "input" : TagIdList,
        "output" : TaskList,
        "description" : "Gets a list of tasks with certain tags",
        "function" : list_tasks_by_tags
    },
    "get_current_datetime" : {
        "input" : NullModel,
        "output" : CurrentDateTime,
        "description" : "The current date and time, assuming located in US Pacific Time Zone",
        "function" : get_current_datetime
    },
    "load_okrs_into_context" : {
        "input" : NullModel,
        "output" : OKRSet,
        "description" : "My OKRs, with measurable key results for each objective",
        "function" : load_okrs_into_context
    },
    "get_all_tasks" : {
        "input" : NullModel,
        "output" : TaskList,
        "description" : "Get all tasks",
        "function" : get_all_tasks
    }
}

def pydantic_to_json_schema(model: BaseModel) -> Dict[str, Any]:
    schema = model.schema()
    # Remove Pydantic-specific keys
    for key in ['title', 'description']:
        schema.pop(key, None)
    return schema

# Now, let's create the array of tools
tools = []

for func_name, func_info in function_io_map.items():
    input_type = func_info['input']
    output_type = func_info['output']
    description = func_info['description']
    
    tool = {
        "name": func_name,
        "description": description,
        "input_schema": pydantic_to_json_schema(input_type)
    }
    
    tools.append(tool)

# Print the resulting tools array
# print(json.dumps(tools, indent=2))


def process_tool_call(tool_name, tool_input):
    if tool_name not in function_io_map:
        raise ValueError(f"Unknown tool: {tool_name}")

    func_info = function_io_map[tool_name]
    input_model = func_info['input']
    output_model = func_info['output']
    function = func_info['function']

    try:
        # Validate and create input object
        validated_input = input_model(**tool_input)
    except ValidationError as e:
        return {"error": f"Invalid input: {str(e)}"}

    # Call the function directly using the reference from function_io_map
    result = function(validated_input)

    # Check if the result is of the expected output type
    if not isinstance(result, output_model):
        return {"error": f"Function returned unexpected type. Expected {output_model.__name__}, got {type(result).__name__}"}

    return result.dict()

################################################################################
## Do the anthropic part

from anthropic import Anthropic
from anthropic.types import (
    ContentBlock,
    ContentBlockDeltaEvent,
    ContentBlockStartEvent,
    ContentBlockStopEvent,
    ImageBlockParam,
    InputJsonDelta,
    Message,
    MessageDeltaEvent,
    MessageDeltaUsage,
    MessageParam,
    MessageStartEvent,
    MessageStopEvent,
    MessageStreamEvent,
    RawContentBlockDeltaEvent,
    RawContentBlockStartEvent,
    RawContentBlockStopEvent,
    RawMessageDeltaEvent,
    RawMessageStartEvent,
    RawMessageStopEvent,
    RawMessageStreamEvent,
    TextBlock,
    TextBlockParam,
    TextDelta,
    ToolResultBlockParam,
    ToolUseBlock,
    ToolUseBlockParam,
    Usage,
)
from anthropic import AnthropicBedrock

# client = Anthropic()
# MODEL_NAME = "claude-3-5-sonnet-20240620"
client = AnthropicBedrock()
MODEL_NAME= "anthropic.claude-3-5-sonnet-20240620-v1:0"


tc1 = TaskCreate(task_name = "Test task anthropic 1",
                 task_description = "The descr of TTA1")

tc2 = TaskCreate(task_name = "Test task anthropic 2",
                 task_description = "The descr of TTA2")



from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown

console = Console()

def print_function_io_map(function_io_map):
    console = Console()

    table = Table(title="Function I/O Map", show_header=True, header_style="bold magenta")
    table.add_column("Function Name", style="cyan", no_wrap=True)
    table.add_column("Input Type", style="green")
    table.add_column("Output Type", style="yellow")
    table.add_column("Description", style="blue")

    for func_name, func_info in function_io_map.items():
        table.add_row(
            func_name,
            func_info['input'].__name__,
            func_info['output'].__name__,
            Text(func_info['description'], style="italic")
        )

    console.print(Panel(table, expand=False, border_style="red"))

def handle_response_list(response_content, conversation_history, debug=False):
    """
    Print out the response, processing a tool call and adding it to the history if necessary.

    TODO Fix - this needs to be a list.
    It needs to build up a user response for each tool_use_block
    """
    used_tools_flag = False
    tool_use_element = {
        "role" : "user",
        "content" : []
    }

    for r0 in response_content:
        # Handle TextBlock and ToolUseBlock specially
        if type(r0) == TextBlock:
            console.print(Panel(Markdown(str(r0.text)), title="Agent response", expand=False))
        elif type(r0) == ToolUseBlock:
            used_tools_flag = True
            tool_use_id = r0.id
            tool_name  = r0.name
            tool_input = r0.input
            if debug:
                console.print(f"\n[bold magenta]Tool Used:[/bold magenta] {tool_name}")
                console.print(Panel(json.dumps(tool_input, indent=2), title="Tool Input", expand=False))
                console.print(f"\n[bold magenta]...calling tool [/bold magenta] {tool_name}")

            tool_result = process_tool_call(tool_name, tool_input)
            if debug:
                console.print(Panel(json.dumps(tool_result, indent=2), title="Tool Result", expand=False))

            # Add the assistant's response and tool use to the conversation history
            tool_use_element['content'].append(
                {
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": str(tool_result),
                })

        else: ## Block type that we do not understand
            console.print(f"\n[bold orange]Different block type")
            console.print(Panel(str(r0)))

    if used_tools_flag:
        conversation_history.append(tool_use_element)

    return conversation_history
    

def chatbot_interaction(user_message, conversation_history, debug=False):

    console.print(Panel(f"[bold blue]User Message:[/bold blue] {user_message}", expand=False))
    
    # Add the new user message to the conversation history and ask the question
    conversation_history.append({"role": "user", "content": user_message})

    response = client.messages.create(
        model=MODEL_NAME,
        max_tokens=200000,
        tools=tools,
        messages=conversation_history
    )
    
    console.print("\n[bold green]Initial Response:[/bold green]")
    resp_type_list = [str(type(x)) for x in response.content]
    console.print(f"\n[bold green]{str(resp_type_list)}[/bold green]")

    # console.print(Panel(Markdown(str(response.content)), title="Content", expand=False))
    conversation_history.append({"role": "assistant", "content": response.content})

    if debug:
        console.print(f"[yellow]Stop Reason:[/yellow] {response.stop_reason}")

    if response.stop_reason == 'tool_use':
        while response.stop_reason == 'tool_use':

            conversation_history = handle_response_list(response.content, conversation_history, debug=debug)

            ## We we are using a tool, we need to follow up.
            response2 = client.messages.create(
                model=MODEL_NAME,
                max_tokens=4096,
                tools=tools,
                messages=conversation_history
            )
            console.print("\n[bold green]Tool Follow-up Response:[/bold green]")
            console.print(f"[yellow]Stop Reason:[/yellow] {response2.stop_reason}")

            # Add the final assistant's response to the conversation history
            conversation_history.append({"role": "assistant", "content": response2.content})
            
            # Keep iterating while we have tools
            response = response2

        ## Finally, once I have excited the while loop, inject the last thing into the history
        conversation_history = handle_response_list(response.content, conversation_history, debug=debug)
        
    else: ## For some other stop reason. This handles that we haven't even gone into the tool_use
          ## while loop
        console.print(f"[yellow]Stop Reason (else):[/yellow] {response.stop_reason}")
        # console.print(Panel(Markdown(str(response.content)), title="Content", expand=False))
        conversation_history = handle_response_list(response.content, conversation_history, debug=debug)
            
    return None , conversation_history

def prompt_continuation(width, line_number, wrap_count):
    """
    The continuation: display line numbers and '->' before soft wraps.

    Notice that we can return any kind of formatted text from here.

    The prompt continuation doesn't have to be the same width as the prompt
    which is displayed before the first line, but in this example we choose to
    align them. The `width` input that we receive here represents the width of
    the prompt.
    """
    if wrap_count > 0:
        return " " * (width - 3) + "-> "
    else:
        text = ("- %i - " % (line_number + 1)).rjust(width)
        return HTML("<strong>%s</strong>") % text

def prompt_continuation_dots(width, line_number, is_soft_wrap):
    return '.' * width
    # Or: return [('', '.' * width)]


def multiline_input(prompt_text):
    console.print(prompt_text)
    answer = prompt(
        "Multiline input: ", multiline=True, prompt_continuation=prompt_continuation_dots
    )
    return answer

def generate_session_id():
    return str(uuid.uuid4())

def save_session(session_id, conversation_history, filename="session.pickle"):
    session_data = {
        "session_id": session_id,
        "conversation_history": conversation_history
    }
    with open(filename, "wb") as f:  # Note the "wb" mode for writing binary
        pickle.dump(session_data, f)
    console.print(f"[bold green]Session saved: {session_id}[/bold green]")

def load_session(filename="session.pickle"):
    if os.path.exists(filename):
        with open(filename, "rb") as f:  # Note the "rb" mode for reading binary
            session_data = pickle.load(f)
        console.print(f"[bold green]Loaded existing session: {session_data['session_id']}[/bold green]")
        return session_data["session_id"], session_data["conversation_history"]
    return None, None

def main():
    console.print("[bold cyan]Welcome to the Task Management System![/bold cyan]")

    
    # Try to load an existing session, or create a new one if it doesn't exist
    session_id, conversation_history = load_session()
    if session_id is None:
        session_id = generate_session_id()
        conversation_history = []
        console.print(f"[bold green]Created new session: {session_id}[/bold green]")
    else:
        console.print(f"[bold green]Loaded existing session: {session_id}[/bold green]")

    console.print(f"[bold blue]Tools:[/bold blue]")
    for k,v in function_io_map.items():
        console.print(f"\t[blue]{k}[/blue]: {v['description']}")        


    while True:
        user_input = multiline_input("\nWhat would you like to do? (Type 'exit' to quit): ")
        
        if user_input.lower() == 'exit':
            console.print("[bold cyan]Thank you for using the Task Management System. Goodbye![/bold cyan]")
            save_session(session_id, conversation_history)
            break
        
        if not user_input:
            console.print("[bold red]Empty input. Please type a message or 'exit' to quit.[/bold red]")
            continue
        
        _ , conversation_history = chatbot_interaction(user_input, conversation_history)

        # # Save the session after each interaction
        # save_session(session_id, conversation_history)
        # md = Markdown(
        #     response,
        #     code_theme="monokai"
        # )
        ### We should not need the above, because all printing happens in the input function
        # # Print the markdown inside a panel
        # console.print(Panel(md, title="[bold green]Chatbot response:[/bold green]", expand=False))

if __name__ == "__main__":
    main()

