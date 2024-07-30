from typing import Dict, List, Any, Optional, Tuple
from typing_extensions import Annotated
from pydantic import BaseModel, Field
from datetime import datetime, timedelta

class Priority(BaseModel):
    color: Optional[str]
    id: Optional[str]
    orderindex: Optional[str]
    priority: Optional[str]

class Task(BaseModel):
    name: str
    id: str
    priority: Optional[Priority]
    date_created: datetime
    date_done: Optional[datetime]
    date_closed: Optional[datetime]
    due_date: Optional[datetime]
    start_date: Optional[datetime]
    time_estimate: Optional[str]
    status: str
    description: str
    tags: List[str]

class TaskList(BaseModel):
    task_list: List[Task]
    current_datetime: datetime

class TaskIdModel(BaseModel):
    task_id: str

class TaskUpdateModel(BaseModel):
    task_id: str
    updated: bool

class TaskAddComment(BaseModel):
    task_id: str
    comment: str

class TaskTags(BaseModel):
    task_id: str
    tag_ids: List[str]

class TaskUpdate(BaseModel):
    task_id: str                     = Field(..., description="The unique identifier of the task to be updated")
    name: Optional[str]              = Field(None, description="The new name of the task")
    description: Optional[str]       = Field(None, description="The new description of the task")
    markdown_description: Optional[str]  = Field(None, description="The new description of the task with Markdown formatting. Use this field instead of description when the input contains markdown formatting or a table.")
    status: Optional[str]            = Field(None, description="The new status of the task")
    priority: Optional[int]          = Field(None, description="The new priority level of the task")
    due_date: Optional[str]          = Field(None, description="The new due date of the task in string format")
    due_date_millis: Optional[int]   = Field(None, description="The new due date of the task in milliseconds since epoch")
    due_date_time: Optional[bool]    = Field(None, description="Whether the due date includes a time component")
    parent: Optional[str]            = Field(None, description="The ID of the new parent task")
    time_estimate: Optional[int]     = Field(None, description="The new time estimate for the task in milliseconds")
    start_date: Optional[str]        = Field(None, description="The new start date of the task in string format")
    start_date_millis: Optional[int] = Field(None, description="The new start date of the task in milliseconds since epoch")
    start_date_time: Optional[bool]  = Field(None, description="Whether the start date includes a time component")

class TaskCreate(BaseModel):
    task_name: str
    task_description: str
    

class WeekToDateTasksInput(BaseModel):
    skip_past_due: bool = Field(False, description="Whether to skip past due tasks")    

class TagIdList(BaseModel):
    tag_ids: List[str]


class NullModel(BaseModel):
    value: None = None

    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: Any) -> 'NullModel':
        if v is not None:
            raise ValueError('Value must be None')
        return cls()

    
class CurrentDateTime(BaseModel):
    current_datetime: datetime


class KeyResult(BaseModel):
    tag_id: str                  = Field(..., description="ClickUp tag ID for the key result")
    description: str             = Field(..., description="Detailed description of the key result")
    frequency: str               = Field(..., description="How often the key result should be measured or achieved (e.g., weekly, monthly)")

class OKR(BaseModel):
    tag_id: str                  = Field(..., description="ClickUp tag ID for the OKR")
    objective: str               = Field(..., description="The main objective or goal of the OKR")
    initiatives: str             = Field(..., description="Specific initiatives or strategies to achieve the objective")
    key_results: List[KeyResult] = Field(..., description="List of key results associated with this OKR")

class OKRSet(BaseModel):
    name: str                    = Field(..., description="Name of the person or entity associated with these OKRs")
    period: str                  = Field(..., description="Time period for which these OKRs are defined (e.g., Q3'24)")
    okrs: List[OKR]              = Field(..., description="List of OKRs for the specified period")

class TaskStatus(BaseModel):
    task_id: str                 = Field(..., description="The unique identifier of the task to be updated")
    status: str                  = Field(..., description="The status of the stask. Possible values are 'open', 'in progress', 'review', 'waiting', 'cancelled', and 'completed'")
