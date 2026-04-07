# Individual Report: Lab 3 - Chatbot vs ReAct Agent

- **Student Name**: Nguyễn Mạnh Dũng
- **Student ID**: 2A202600177
- **Date**: 06/04/2026

---

## I. Technical Contribution (15 Points)

*Describe your specific contribution to the codebase (e.g., implemented a specific tool, fixed the parser, etc.).*

- Used GenAI to create mock data: data/mock_data.json
- Implemented core functions in src/tools/menu_tool.py
- Wrote the system prompt for agent v2: src/agent/agent_v2.py

- **Modules Implementated**: src/tools/menu_tool.py
- **Code Highlights**: 
+ `calculating_total_bill()` automatically selects the best available discount and returns the post-discount total, including stock checks. `src/tools/menu_tool.py:461`
+ `compare_items_vs_combo()` compares item-by-item pricing versus a combo, including optimal discount selection for each option. `src/tools/menu_tool.py:393`

- **Documentation**: 
These functions are registered as tools in the ReAct agent and invoked via OpenAI tool calling. The agent defines tool schemas in `src/agent/agent_v2.py:200`, then when the model emits `tool_calls`, the agent executes the tool and returns the result as a `role=tool` message to continue reasoning. `src/agent/agent_v2.py:100`


---

## II. Debugging Case Study (10 Points)

*Analyze a specific failure event you encountered during the lab using the logging system.*

- **Problem Description**: The agent failed with a 400 BadRequest when calling OpenAI tool calling due to an invalid function schema.
- **Log Source**: Terminal error snippet during `chat.completions.create`:
  ```
  openai.BadRequestError: Error code: 400 - {'error': {'message': "Invalid schema for function 'get_item': In context=(), 'additionalProperties' is required to be supplied and to be false.", 'type': 'invalid_request_error', 'param': 'tools[0].function.parameters', 'code': 'invalid_function_parameters'}}
  ```
- **Diagnosis**: The tool schema did not comply with OpenAI strict function calling requirements. Missing `additionalProperties: false` and incomplete `required` arrays caused schema validation to fail before the model could run.
- **Solution**: Updated all tool schemas in `src/agent/agent_v2.py` to include `additionalProperties: false` and `required` lists that include all declared properties (and nested object properties), which resolved the 400 error.

---
## III. Personal Insights: Chatbot vs ReAct (10 Points)

*How would you scale this for a production-level AI agent system?*

1.  **Reasoning**: The Thought structure helped the agent break tasks into tool calls and verify results instead of guessing like a direct chatbot response.
2.  **Reliability**: The agent performed worse on simple questions when tool-calling failed or schema errors blocked execution, while the chatbot could still answer.
3.  **Observation**: Tool observations grounded the next step—errors triggered retries or safe fallbacks, and successful outputs guided final responses.


## IV. Future Improvements (5 Points)

*How would you scale this for a production-level AI agent system?*

1.  **Scalability**: Add async job queues and caching for tool calls to handle higher concurrency.
2.  **Safety**: Use a supervisor/guardrail model to validate tool calls and final answers.
3.  **Performance**: Add retrieval (vector DB) for faster tool selection and domain knowledge lookup.

---
