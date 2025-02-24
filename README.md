# Fine-Tuning LLMs for Context-Aware Story Continuation with Reasoning

## Abstract
This post presents a methodology for fine-tuning large language models to improve context-aware story continuation by incorporating reasoning steps. The approach leverages publicly available books from the Project Gutenberg corpus, processes them into structured training data, and fine-tunes models like Qwen2.5 Instruct (7B and 32B) using a cost-effective pipeline (qLoRA). The resulting models demonstrate improved story continuation capabilities, generating a few sentences at a time while maintaining narrative coherence. The fine-tuned models are made available in GGUF format for accessibility and experimentation. This work is planned to be part of writer-assistant tools (to be developer and published later) and encourages community feedback for further refinement.

---

## Introduction
While text continuation is literally the main purpose of LLMs, story continuation is still a challenging task, as it requires understanding narrative context, characters' motivations, and plot progression. While existing models can generate text, they often lack the ability to progress the story's flow just in the correct amount when continuing it, they often do nothing to progress to plot, or too much in a short amount of time. This post introduces a fine-tuning methodology that combines reasoning steps with story continuation, enabling models to better understand context and produce more coherent outputs. The approach is designed to be cost-effective, leveraging free and low-cost resources while only using public domain or synthetic training data.

---

## Methodology

### 1. Data Collection and Preprocessing
- **Source Data:** Public domain books from the Project Gutenberg corpus, written before the advent of LLMs were used to make avoid contamination from modern AI-generated text.
- **Chunking:** Each book was split into chunks of ~100 sentences, where 80 sentences were used as context and the subsequent 20 sentences as the continuation target.

### 2. Thought Process Generation
- **Prompt Design:** Two prompt templates were used:
  1. **Thought Process Template:** Encourages the model to reason about the story's flow, character motivations, and interactions.
  2. **Continuation Template:** Combines the generated reasoning with the original continuation to create a structured training example. This becomes the final training data, which is built from 4 parts: 
     - **Static part:** System prompt and Task parts are fix.
     - **Context:** Context is the first 80 sentences of the chunk (Human-written data)
     - **Reasoning:** Synthetic reasoning part, written DeepSeek v3 model on OpenRouter was used to generate thought processes for each chunk, because it follows instructions very well and it is cheap.
     - **Response:** The last 20 sentences of the training data 

### 3. Fine-Tuning
- **Model Selection:** Qwen2.5 Instruct (7B and 32B) was chosen for fine-tuning due to its already strong performance and permissive licensing.
- **Training Pipeline:** LoRA (Low-Rank Adaptation) training was performed on Fireworks.ai, as currently their new fine-tuning service is free.
- **Note:** Please note that GRPO (Used for reasoning models like DeepSeek R1) was not used for this experiment. 

### 4. Model Deployment
- **Quantization:**  Fireworks' output are safetensor adapters, these were first converted to GGUF adapters, then merged into the base model. For the 7B variant, the adapter was merged into the F16 base model, then quantized into Q4, with the 32B model, the adapter was directly merged into Q4 base model. Conversion and merging was done with llama.cpp.
- **Distribution:** Models were uploaded to Ollama and Hugging Face for easy access and experimentation.

---

## Results
The fine-tuned models demonstrated improvements in story continuation tasks:
- **Contextual Understanding:** The models effectively used reasoning steps to understand narrative context before generating continuations.
- **Coherence:** Generated continuations were more coherent and aligned with the story's flow compared to baseline models.
- **Efficiency:** The 7B model with 16k context fully offloads to my laptop's GPU (RTX 3080 8GB) and manages  

---

## Discussion
### Strengths
- **Cost-Effective:** The use of free and low-cost resources makes the approach accessible to a wide audience.
- **Scalable:** The methodology can be applied to larger datasets and models for further improvements.
- **Practical:** The fine-tuned models are lightweight and compatible with consumer hardware, enabling real-world applications.
- **Training data** is published at: https://huggingface.co/datasets/molbal/reasoning-story-completion
  - Note: This training dataset is random books. For the published models I cherry-picked books to serve as corpus including some of my own unpublished writing.

### Limitations
- **Dataset Bias:** The use of pre-LLM-era books may introduce biases or outdated language patterns.
- **Reasoning Quality:** The quality of generated reasoning depends on the output of DeepSeek V3 model, which may carry its own biases and imperfections.

---

## Future Work
- **Dataset Expansion:** Incorporate more diverse and modern texts to reduce bias and improve generalization.
- **Reasoning Enhancement:** Explore alternative methods for generating higher-quality reasoning steps.
- **Guided generation:** Experiment with ways to better guide the direction of the model's output.
- **Set generation length:** Add some mechanic to control generation length.
- **User Feedback:** Integrate the models into a writer-assistant tool and gather user feedback for iterative improvements.

---

## Test
I invite the community to try the fine-tuned models and provide feedback. The models are available on Ollama Hub ([7B](https://ollama.com/molbal/cra-v1-7b), [32B](https://ollama.com/molbal/cra-v1-32b)) and Hugging Face ([7B](https://huggingface.co/molbal/CRA-v1-7B), [32B](https://huggingface.co/molbal/CRA-v1-32B)).

Note: The 32B F16 version is not uploaded to Hugging Face, only Ollama Hun.

For best results, please keep the following prompt format. Do not omit the System part either.
```text
### System: You are a writer’s assistant.

### Task: Understand how the story flows, what motivations the characters have and how they will interact with each other and the world as a step by step thought process before continuing the story.

### Context:
{context}
```
The model will reliably respond in the following format
```xml
<reasoning>
    Chain of thought.
</reasoning>
<answer>
    Text completion
</answer>
```


---

## References
- Project Gutenberg: https://www.gutenberg.org
- OpenRouter: https://openrouter.ai
- Fireworks.ai: https://docs.fireworks.ai/fine-tuning/fine-tuning-models
- Qwen2.5: https://huggingface.co/Qwen/Qwen2.5-7B-Instruct and https://huggingface.co/Qwen/Qwen2.5-32B-Instruct
- LLama.cpp: https://github.com/ggml-org/llama.cpp
- My blog: https://molbal94.substack.com/