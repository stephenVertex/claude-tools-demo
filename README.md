# Claude Tools ClickUp Task Manager

This repository demonstrates how to use Anthropic's Claude AI model with custom tools to manage tasks in ClickUp. The project showcases the integration of Claude's powerful language capabilities with practical task management functionalities.

## Features

- Interact with Claude to manage ClickUp tasks
- Demo OKRs for Michael Scott from The Office (for testing and demonstration purposes)
- Utilizes Pydantic for data validation and serialization
- Implements a flexible tool system for extending functionalities

## Key Components

### Pydantic Models

The project extensively uses Pydantic for data validation and serialization. This ensures type safety and provides clear structures for input and output data.

### Function I/O Map

The `function_io_map` is a central component that defines the available tools, their input/output types, and descriptions. Here's an example of how it's structured:

```python
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
    # ... other functions ...
}
```

## Adding New Tools

To add a new tool to the system:

1. Create Pydantic models for the input and output of your new tool.
2. Implement the tool function.
3. Update the `function_io_map` with the new tool information.

Example:

```python
# Step 1: Create Pydantic models
class NewToolInput(BaseModel):
    param1: str
    param2: int

class NewToolOutput(BaseModel):
    result: str

# Step 2: Implement the tool function
def new_tool_function(input_data: NewToolInput) -> NewToolOutput:
    # Implementation here
    pass

# Step 3: Update function_io_map
function_io_map["new_tool_name"] = {
    "input": NewToolInput,
    "output": NewToolOutput,
    "description": "Description of what the new tool does",
    "function": new_tool_function
}
```

## Michael Scott's OKRs

The project includes a set of demo Objectives and Key Results (OKRs) for Michael Scott from The Office. These are used for testing and demonstration purposes, showcasing how the system can handle real-world-like goal setting and task management scenarios.

## Usage

[Include instructions on how to set up and run the project]

## Dependencies

- Anthropic Claude API
- Pydantic
- ClickUp API
- [List other major dependencies]

## Contributing

Hey there! 👋 We're stoked to see you're interested in contributing. Whether you're fixing bugs, adding features, or improving docs, your input is valuable. Fork the repo, make your changes, and submit a pull request - we can't wait to see what you come up with! If you're new to this, don't worry; we're here to help you get started.

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

The Apache License 2.0 is a permissive free software license written by the Apache Software Foundation. It allows users to use the software for any purpose, to distribute it, to modify it, and to distribute modified versions of the software under the terms of the license, without concern for royalties.

Key points of the Apache License 2.0:

- You can freely use, modify, and distribute this software.
- You can use it for commercial purposes.
- You don't have to share the source code of your modifications.
- You must include a copy of the license in any redistribution you may make that includes the software.
- You must indicate significant changes made to the software.
- You must include a notice file that specifies attribution, modification notices, and a disclaimer.

For the full license text, please refer to the [Apache License 2.0](https://www.apache.org/licenses/LICENSE-2.0) official page or the LICENSE file in this repository.
