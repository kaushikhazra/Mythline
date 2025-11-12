## General Instructions
The graph system is a Finite State Machine. The should be designed based on Nodes. Each node represents a state, and performed certain operation. Once the operation is done, it either returns another node, or returns "End" node. In a way it works like an advance version of linked list.

```
Node 1 --> Node 2 --> End
```

### Conditional State Transfer
A state can direct to more than one states based on condition.

```
Node 1 --<normal flow>--> Node 2
    |
    | <conditional flow>
    |
    +------> Node 3
```

### Loop
A loop is absolutely possible, however it is moving from one state to another and coming back.

```
Node 1 ---> Node 3
  ^           |
  |           |
  +-----------+
```

Self looping is rare, however it can be useful at some time. For example, if a state accepts accepts user input then it can check for valid input and when then check fails it can loop back to itself for valid input.

```
Enter Data -+
    ^       |
    |       |<invalid value>
    +-------+
```

## Structuring A Pydantic Graph
1. Define the Nodes
2. Insert correct logic
3. Link the node to another node by returning them
4. Return built in "End" state if all done.

## Defining Nodes

### Simple Node
```python
from __future__ import annotations
from dataclasses import dataclass

from pydantic_graph import BaseNode, GraphRunContext

@dataclass
class {Node_Nmae}(BaseNode):
    async def run(self, ctx:GraphRunContext) -> Next_State:
        # Logic goes here
        return Next_state(required_args)
```

### Node With Branching
```python
from __future__ import annotations
from dataclasses import dataclass

from pydantic_graph import BaseNode, End, GraphRunContext

@dataclass
class {Node_Nmae}(BaseNode):
    async def run(self, ctx:GraphRunContext) -> State1 | State2 | End[str]:
        # Logic goes here
        if condition1:
            return State1(required_args)
        elif condition2:
            return State2(required_args)
        else:
            return End(output)
```
## Invoking A Graph
This code always goes into `graph.py` file in the proper graph folder
```python
from pydantic_graph import Graph
from src.graphs.{some_graph_name}.{some_node_group} import Node1, Node2...

class {GraphName}:
    def __init__(self, ...):
        # Any other logic goes here
        self.graph = Graph(nodes=[Node1, Node2, ...])
        # Any other logic goes here

    def run(...) -> {TheOutputType}:
        # Any logic goes here
        result = self.graph.run_sync(Node1())
        return result.output
```
The above class can be used anywhere we need to run the graph as a workflow.

## Gen AI With Pydantic Graph
Calling an AI agent from a Pydantic graph is a little bit of involved operation. Ideally the steps are simple, define the node, call the agent, receive the output, return the next node or End node with output.

However, to make the operation more structured a little bit of more programming is needed:

1. Define an output model
2. Define an agent using OOP approach, that will return the output model. Follow the `pydapydantic_ai_agent_guide.md` for more details on how to create an agent, except the output model part. Output model is described below.
3. Define the node for the graph that will use the agent.
4. Invoke the agent using `run()` method. It needs to be async operation
5. Once the result is generated, process the output
6. Branch if branching is needed, end if the execution is done, or move linearly to next node.

### Structure Of The Output Model
```python
from dataclasses import dataclass
from pydantic import BaseModel

@dataclass
class {Output_Model_Name}(BaseModel):
    #properties goes here
```

### Defining The Agent
The agent should follow OOP approach mentioned in the `pydapydantic_ai_agent_guide.md`
```python
class {AgentName}:
    def __init__(self,...):
        ...
        self.{agent_name} = Agent(  
            llm_model,
            output_type={Output_Model_Name},
            ...
        ...
    # Other member methods goes here
)
```

### Defining The Node
```python
@dataclass
class {NodeName}(BaseNode):
    # Member variables goes here
    # These variables can be set when this node is invokes
    # for example: Node(member_arg)

    def __init__(self,...):
        self.{agent_name} = AgentName(...)

    async def run(self, ctx:GraphRunContext) -> Node1 | Node2:
        
        result = await self.{agent_name}.run(self.prompt)
        output = result.output

        if output.{some_var_from_the_model}:
            # Can put prints if needed with proper color using "colored"
            return Node1(output | output.{some_var})
        else:
            # Can put prints if needed with proper color using "colored"
            return Node2(output | output.{some_var})
```

## State Management (Stateful Graphs)
Pydantic graph can managed states. This is useful when information needs to be persisted across states, and shared between each other.

State management is done using:
1. Defining a dataclass that can hold session or state information
2. Passing that data class as a generics during node at the super class
3. Access the information using graph context

```python
@dataclass
class SessionFor{GraphName}:
    # The properties goes here
    name_of_the_property: type

@dataclass
class {NodeName}(BaseNode[SessionFor{GraphName}]):
    ...
    async def run(
        self, 
        ctx:GraphRunContext[SessionFor{GraphName}]
    ) -> {ReturnNode} | ...:
        # access the session vars
        var1 = cts.state.{name_of_the_property}
        # set something to the vars
        cts.state.{name_of_the_property} = var2
```