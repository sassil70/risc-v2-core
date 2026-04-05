import os
import logging
from jinja2 import Environment, FileSystemLoader, select_autoescape

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PromptEngine")

class PromptEngine:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PromptEngine, cls).__new__(cls)
            cls._instance._initialize()
        return cls._instance

    def _initialize(self):
        # Setup Jinja2 Environment
        # Path assumes we are in services/, templates are in ../prompts/templates
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        self.template_dir = os.path.join(base_dir, "prompts", "templates")
        
        try:
            self.env = Environment(
                loader=FileSystemLoader(self.template_dir),
                autoescape=select_autoescape(['html', 'xml'])
            )
            logger.info(f"PromptEngine Initialized. Templates at: {self.template_dir}")
        except Exception as e:
            logger.error(f"Failed to init PromptEngine: {e}")
            raise e

    def render_prompt(self, template_name: str, context_data: dict) -> str:
        """
        Renders a Jinja2 template with provided context.
        template_name: e.g. 'context_outside.j2'
        context_data: dict containing keys like 'rics_knowledge_context'
        """
        try:
            template = self.env.get_template(template_name)
            return template.render(**context_data)
        except Exception as e:
            logger.error(f"Template Rendering Error ({template_name}): {e}")
            # Fallback to a safe error prompt? Or raise?
            return f"ERROR RENDERING PROMPT: {e}"

def get_prompt_engine():
    return PromptEngine()
