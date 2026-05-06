import argparse, functools
import gradio as gr
from diffusers.utils import load_image, make_image_grid
import torch

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_dir", type=str, required=True)
    return parser.parse_args()
args = parse_args()

def _get_prompt(position, class_name):
    class_prompt = '' if class_name == 'unknown' else "inspired by the shapes of {}, ".format(class_name)
    prompt_template = "A pattern design at {} position, {}graphic design, black and white, minimalistic, sharp lines, vector art, high contrast, industrial design, clean and organized."
    return prompt_template.format(position, class_prompt)

def get_pipeline(model_dir):
    from diffusers import AutoPipelineForText2Image
    pipeline = AutoPipelineForText2Image.from_pretrained("stable-diffusion-v1-5/stable-diffusion-v1-5", dtype=torch.float16,
                                                         safety_checker=None).to("cuda")
    pipeline.load_lora_weights(model_dir, weight_name="pytorch_lora_weights.safetensors")
    return pipeline

pipeline = get_pipeline(args.model_dir)

def generate_images(position, class_name, width, height, num_inference_steps, num_images, progress=gr.Progress(track_tqdm=True)):
    images = []
    neg_prompt = "Text, blurry, out of focus, complex, color, noisy, multiple patterns, low quality, photo, realistic, messy, hand drawn, watercolor, text, noise, low resolution."
    try:
        images = pipeline(_get_prompt(position, class_name), num_inference_steps=num_inference_steps, negative_prompt=neg_prompt,
                      width=width, height=height, num_images_per_prompt=num_images).images
    except Exception as e:
        print(f"Error during image generation: {e}")

    return images

# Create the Gradio interface
inputs=[
    gr.Radio(label="Position", choices=["center", "side"], value="center"),
    gr.Textbox(label="Class", lines=1, value="unknown"),
    gr.Slider(label="Width", minimum=64, maximum=1024, step=1, value=128),
    gr.Slider(label="Height", minimum=64, maximum=1024, step=1, value=128),
    gr.Slider(label="The number of inference steps", minimum=10, maximum=100, step=1, value=50),
    gr.Slider(label="The number of images to generate", minimum=1, maximum=64, step=1, value=8),
]

iface = gr.Interface(
    fn=generate_images,
    inputs=inputs,
    outputs=gr.Gallery(label="Generated Images"),
    title="Stable Diffusion Web Demo",
    description="Generate images from a text prompt using a Stable Diffusion model.",
    allow_flagging="auto" # or "never" if you don't want a flagging button
)

# Launch the Gradio app
if __name__ == "__main__":
    iface.launch(debug=True, share=False, server_name="0.0.0.0", server_port=7860)