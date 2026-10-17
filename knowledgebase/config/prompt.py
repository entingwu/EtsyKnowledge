# System Prompt
ITEM_NAME_SYSTEM_PROMPT = "You are a professional product name recognition model. Identify the product name based on the information provided."

# User Prompt Template
ITEM_NAME_USER_PROMPT_TEMPLATE = """
               Identify the product name and model from the following information:
               File name: {file_title}

               Content chunks (to assist identification):
               {context}

               Requirements:
               1. Return a plain string, ideally the complete product name including brand, model and name;
               2. Return only the product name, without any explanation or other content;
               3. If the product name cannot be identified, return an empty string;
               4. Use the original language of the content (English content returns English) and do not translate; prefer the product name in the document's top-level heading.
               """
