"""Isolated selector definitions for Google Flow UI."""

SIGN_IN_BUTTON_SELECTORS = [
    "a:has-text('Sign in')",
    "button:has-text('Sign in')",
    "a:has-text('Log in')",
    "[aria-label*='Sign in']",
]

AUTH_INDICATOR_SELECTORS = [
    "[aria-label*='Google Account']",
    "img[alt*='Google Account']",
    "[data-identifier]",
    "#profile-identifier",
    "button[aria-label*='Account']",
    "div[role='banner']",
]

NEW_PROJECT_SELECTORS = [
    "button:has-text('New project')",
    "button:has-text('Create project')",
    "button:has-text('New')",
    "[aria-label*='New project']",
    "[aria-label*='Create project']",
]

IMAGE_MODE_SELECTORS = [
    "button:has-text('Image')",
    "[role='tab']:has-text('Image')",
    "[aria-label='Image mode']",
    "[aria-label='Select Image']",
    "div[role='button']:has-text('Image')",
]

MODEL_DROPDOWN_SELECTORS = [
    "button[aria-label*='Model']",
    "button:has-text('Model')",
    "[data-testid='model-selector']",
    "div[role='combobox'][aria-label*='Model']",
    "button:has-text('Nano Banana')",
    "button:has-text('Imagen')",
]

NANO_BANANA_2_SELECTORS = [
    "li:has-text('Nano Banana 2')",
    "button:has-text('Nano Banana 2')",
    "[role='option']:has-text('Nano Banana 2')",
    "[role='menuitem']:has-text('Nano Banana 2')",
    "div:has-text('Nano Banana 2')",
    "[data-value*='nano-banana-2']",
    "[data-value*='Nano Banana 2']",
]

ASPECT_RATIO_DROPDOWN_SELECTORS = [
    "button[aria-label*='Aspect ratio']",
    "button[aria-label*='Ratio']",
    "button:has-text('16:9')",
    "button:has-text('1:1')",
    "button:has-text('9:16')",
    "[data-testid='aspect-ratio-selector']",
]

ASPECT_RATIO_OPTIONS = {
    "16:9": [
        "li:has-text('16:9')",
        "[role='option']:has-text('16:9')",
        "button:has-text('16:9')",
        "[data-value='16:9']",
    ],
    "1:1": [
        "li:has-text('1:1')",
        "[role='option']:has-text('1:1')",
        "button:has-text('1:1')",
        "[data-value='1:1']",
    ],
    "9:16": [
        "li:has-text('9:16')",
        "[role='option']:has-text('9:16')",
        "button:has-text('9:16')",
        "[data-value='9:16']",
    ],
}

OUTPUT_COUNT_DROPDOWN_SELECTORS = [
    "button[aria-label*='Outputs']",
    "button[aria-label*='Count']",
    "button[aria-label*='Number of images']",
    "button:has-text('4 images')",
    "button:has-text('Outputs: 4')",
    "[data-testid='output-count-selector']",
]

OUTPUT_COUNT_4_SELECTORS = [
    "li:has-text('4')",
    "[role='option']:has-text('4')",
    "button:has-text('4')",
    "[data-value='4']",
]

PROMPT_INPUT_SELECTORS = [
    "div[role='textbox'][data-slate-editor='true']",
    "div.sc-1c9f7009-0",
    "div[contenteditable='true']",
    "textarea[placeholder*='Describe']",
    "textarea[placeholder*='prompt']",
    "textarea[aria-label*='Prompt']",
    "textarea[aria-label*='Describe']",
    "textarea",
]

GENERATE_BUTTON_SELECTORS = [
    "button:has(i:has-text('arrow_forward'))",
    "button:has-text('Create')",
    "div.sc-5c3af813-10 button.sc-5c3af813-5",
    "button:has-text('Generate')",
    "button[aria-label='Generate']",
    "[data-testid='generate-button']",
    "button[type='submit']",
]

GENERATING_INDICATORS = [
    "button[disabled]:has-text('Generate')",
    "button:has-text('Generating')",
    "div[data-state='generating']",
    "[aria-busy='true']",
    "[role='progressbar']",
    ".loading-spinner",
    "div.sc-5c3af813-10 button[disabled]",
]

QUOTA_ERROR_SELECTORS = [
    "*:has-text('quota exceeded')",
    "*:has-text('daily limit')",
    "*:has-text('too many requests')",
    "*:has-text('generation unavailable')",
    "*:has-text('rate limit')",
    "*:has-text('temporarily unavailable')",
]

GENERATED_IMAGE_CONTAINERS = [
    "div[data-testid='virtuoso-scroller'] img",
    "div.sc-888a6226-1 img",
    "img[src^='blob:']",
    "img[src*='googleusercontent.com']",
    "img[src^='https://']",
    "[data-testid='generated-image']",
    ".generated-image-card",
    "div[role='img']",
]

