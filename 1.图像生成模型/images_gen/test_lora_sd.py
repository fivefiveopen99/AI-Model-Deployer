import argparse

from diffusers import AutoPipelineForText2Image
import torch

def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_dir", type=str, required=True)
    parser.add_argument("--position", type=str, choices=["center", "side"], required=True)
    parser.add_argument("--class_name", type=str, required=True)
    parser.add_argument("--batch_size", type=int, default=10)
    parser.add_argument("--num_inference_steps", type=int, default=50)
    parser.add_argument("--neg_prompt", type=str, required=False, default="Text, blurry, out of focus, complex, color, noisy, multiple patterns, low quality, photo, realistic, messy, hand drawn, watercolor, text, noise, low resolution.")
    parser.add_argument("--disable_lora", action="store_true")
    parser.add_argument("--size", type=str, required=False, default="128")
    return parser.parse_args()

def _get_prompt(position, class_name):
    class_prompt = '' if class_name == 'unknown' else "inspired by the shapes of {}, ".format(class_name)
    prompt_template = "A pattern design at {} position, {}graphic design, black and white, minimalistic, sharp lines, vector art, high contrast, industrial design, clean and organized."
    return prompt_template.format(position, class_prompt)

def main(args):
    pipeline = AutoPipelineForText2Image.from_pretrained("stable-diffusion-v1-5/stable-diffusion-v1-5", dtype=torch.float16,
                                                         safety_checker=None).to("cuda")
    if not args.disable_lora:
        pipeline.load_lora_weights(args.model_dir, weight_name="pytorch_lora_weights.safetensors")
    prompt = _get_prompt(args.position, args.class_name)
    size = args.size.split(",")
    size = [int(s) for s in size if s]
    if len(size) == 1:
        size = size * 2
    images = pipeline(prompt, num_inference_steps=args.num_inference_steps, negative_prompt=args.neg_prompt,
                      width=size[0], height=size[1], num_images_per_prompt=args.batch_size).images
    for i, image in enumerate(images):
        image.save(f"image_{i}.png")

if __name__ == "__main__":
    args = parse_args()
    main(args)