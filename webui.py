import gradio as gr
import requests
import argparse
import json
import pathlib

conn_url = None
conn_key = None

host_url = None

models = []
draft_models = []
loras = []

parser = argparse.ArgumentParser(description="TabbyAPI Gradio Loader")
parser.add_argument("-p", "--port", type=int, default=7860, help="Specify port to host the WebUI on (default 7860)")
parser.add_argument("-l", "--listen", action="store_true", help="Share WebUI link via LAN")
parser.add_argument("-s", "--share", action="store_true", help="Share WebUI link remotely via Gradio's built in tunnel")
args = parser.parse_args()
if args.listen: host_url = "0.0.0.0"

def read_preset(name):
    if not name: raise gr.Error("Please select a preset to load.")
    path = pathlib.Path(f'./presets/{name}.json').resolve()
    with open(path, "r") as openfile:
        data = json.load(openfile)
    gr.Info(f'Preset {name} loaded.')
    return gr.Dropdown(value=data.get("name")), gr.Number(value=data.get("max_seq_len")), gr.Number(value=data.get("override_base_seq_len")), gr.Checkbox(value=data.get("gpu_split_auto")), gr.Textbox(value=data.get("gpu_split")), gr.Number(value=data.get("rope_scale")), gr.Number(value=data.get("rope_alpha")), gr.Checkbox(value=data.get("no_flash_attention")), gr.Radio(value=data.get("cache_mode")), gr.Textbox(value=data.get("prompt_template")), gr.Number(value=data.get("num_experts_per_token")), gr.Dropdown(value=data.get("draft_model_name")), gr.Number(value=data.get("draft_rope_scale")), gr.Number(value=data.get("draft_rope_alpha"))

def del_preset(name):
    if not name: raise gr.Error("Please select a preset to delete.")
    path = pathlib.Path(f'./presets/{name}.json').resolve()
    path.unlink()
    gr.Info(f'Preset {name} deleted.')
    return get_preset_list()

def write_preset(name, model_name, max_seq_len, override_base_seq_len, gpu_split_auto, gpu_split, model_rope_scale, model_rope_alpha, no_flash_attention, cache_mode, prompt_template, num_experts_per_token, draft_model_name, draft_rope_scale, draft_rope_alpha):
    if not name: raise gr.Error("Please enter a name for your new preset.")
    path = pathlib.Path(f'./presets/{name}.json').resolve()
    data = {
        "name" : model_name,
        "max_seq_len" : max_seq_len,
        "override_base_seq_len" : override_base_seq_len,
        "gpu_split_auto" : gpu_split_auto,
        "gpu_split" : gpu_split,
        "rope_scale" : model_rope_scale,
        "rope_alpha" : model_rope_alpha,
        "no_flash_attention" : no_flash_attention,
        "cache_mode" : cache_mode,
        "prompt_template" : prompt_template,
        "num_experts_per_token" : num_experts_per_token,
        "draft_model_name" : draft_model_name,
        "draft_rope_scale" : draft_rope_scale,
        "draft_rope_alpha" : draft_rope_alpha
    }
    with open(path, "w") as outfile:
        json.dump(data, outfile, indent=4)
    gr.Info(f'Preset {name} saved.')
    return gr.Textbox(value=None), get_preset_list()

def get_preset_list(raw = False):
    preset_path = pathlib.Path("./presets").resolve()
    preset_list = []
    for path in preset_path.iterdir():
        if path.is_file() and path.name.endswith(".json"):
            preset_list.append(path.stem)
    if raw: return preset_list
    return gr.Dropdown(choices=preset_list, value=None)

def connect(data):
    global conn_url
    global conn_key
    global models
    global draft_models
    global loras

    try:
        m = requests.get(url=data.get(api_url) + "/v1/model/list", headers={"X-api-key" : data.get(admin_key)})
        m.raise_for_status()
        d = requests.get(url=data.get(api_url) + "/v1/model/draft/list", headers={"X-api-key" : data.get(admin_key)})
        d.raise_for_status()
        l = requests.get(url=data.get(api_url) + "/v1/lora/list", headers={"X-api-key" : data.get(admin_key)})
        l.raise_for_status()
    except:
        raise gr.Error("An error was encountered, please check your inputs and traceback.")
    
    conn_url = data.get(api_url)
    conn_key = data.get(admin_key)

    models = []
    for model in m.json().get("data"):
        models.append(model.get("id"))

    draft_models = []
    for draft_model in d.json().get("data"):
        draft_models.append(draft_model.get("id"))
        
    loras = []
    for lora in l.json().get("data"):
        loras.append(lora.get("id"))

    gr.Info("TabbyAPI connected.")
    return gr.Textbox(value=", ".join(models), visible=True), gr.Textbox(value=", ".join(draft_models), visible=True), gr.Textbox(value=", ".join(loras), visible=True), get_model_list(), get_draft_model_list(), get_lora_list(), get_current_model(), get_current_loras()

def get_model_list():
    return gr.Dropdown(choices=models, value=None)

def get_draft_model_list():
    return gr.Dropdown(choices=draft_models, value=None)

def get_lora_list():
    return gr.Dropdown(choices=loras, value=[])

def get_current_model():
    model_card = requests.get(url=conn_url + "/v1/model", headers={"X-api-key" : conn_key}).json()
    if not model_card.get("id"): return gr.Textbox(value=None)
    params = model_card.get("parameters")
    spec_decode = bool(params.get("draft"))
    model = f'{model_card.get("id")} (context: {params.get("max_seq_len")}, rope scale: {params.get("rope_scale")}, rope alpha: {params.get("rope_alpha")}, speculative decoding: {spec_decode})'
    return gr.Textbox(value=model)

def get_current_loras():
    l = requests.get(url=conn_url + "/v1/lora", headers={"X-api-key" : conn_key}).json()
    if not l.get("data"): return gr.Textbox(value=None)
    lora_list = l.get("data")
    loras = []
    for lora in lora_list:
        loras.append(f'{lora.get("id")} (scaling: {lora.get("scaling")})')
    return gr.Textbox(value=", ".join(loras))

def update_loras_table(loras):
    array = []
    for lora in loras:
        array.append(1.0)
    if array:
        return gr.List(value=[array], col_count=(len(array), "fixed"), row_count=(1, "fixed"), headers=loras, visible=True)
    else:
        return gr.List(value=None, visible=False)

def load_model(model_name, max_seq_len, override_base_seq_len, gpu_split_auto, gpu_split, model_rope_scale, model_rope_alpha, no_flash_attention, cache_mode, prompt_template, num_experts_per_token, draft_model_name, draft_rope_scale, draft_rope_alpha):
    if not model_name: raise gr.Error("Specify a model to load!")
    gpu_split_parsed = []
    try:
        if gpu_split:
            gpu_split_parsed = [float(i) for i in list(gpu_split.split(","))]
    except ValueError:
        raise gr.Error("Check your GPU split values and ensure they are valid!")    
    if draft_model_name:
        draft_request = {
            "draft_model_name" : draft_model_name,
            "draft_rope_scale" : draft_rope_scale,
            "draft_rope_alpha" : draft_rope_alpha
        }
    else:
        draft_request = None
    request = {
        "name" : model_name,
        "max_seq_len" : max_seq_len,
        "override_base_seq_len" : override_base_seq_len,
        "gpu_split_auto" : gpu_split_auto,
        "gpu_split" : gpu_split_parsed,
        "rope_scale" : model_rope_scale,
        "rope_alpha" : model_rope_alpha,
        "no_flash_attention" : no_flash_attention,
        "cache_mode" : cache_mode,
        "prompt_template" : prompt_template,
        "num_experts_per_token" : num_experts_per_token,
        "draft" : draft_request
    }
    try:
        requests.get(url=conn_url + "/v1/model/unload", headers={"X-admin-key" : conn_key})
        r = requests.post(url=conn_url + "/v1/model/load", headers={"X-admin-key" : conn_key}, json=request)
        r.raise_for_status()
        gr.Info("Model successfully loaded.")
        return get_current_model(), get_current_loras()
    except:
        raise gr.Error("An error was encountered, please check your inputs and traceback.")

def load_loras(loras, scalings):
    if not loras: raise gr.Error("Specify at least one lora to load!")
    load_list = []
    for index, lora in enumerate(loras):
        try:
            scaling = float(scalings[0][index])
            load_list.append({"name" : lora, "scaling" : scaling})
        except ValueError:
            raise gr.Error("Check your scaling values and ensure they are valid!")
    request = {"loras" : load_list}
    try:
        requests.get(url=conn_url + "/v1/lora/unload", headers={"X-admin-key" : conn_key})
        r = requests.post(url=conn_url + "/v1/lora/load", headers={"X-admin-key" : conn_key}, json=request)
        r.raise_for_status()
        gr.Info("Loras successfully loaded.")
        return get_current_model(), get_current_loras()
    except:
        raise gr.Error("An error was encountered, please check your inputs and traceback.")

def unload_model():
    try:
        r = requests.get(url=conn_url + "/v1/model/unload", headers={"X-admin-key" : conn_key})
        r.raise_for_status()
        gr.Info("Model unloaded.")
        return get_current_model(), get_current_loras()
    except:
        raise gr.Error("An error was encountered, please check your inputs and traceback.")

def unload_loras():
    try:
        r = requests.get(url=conn_url + "/v1/lora/unload", headers={"X-admin-key" : conn_key})
        r.raise_for_status()
        gr.Info("All loras unloaded.")
        return get_current_model(), get_current_loras()
    except:
        raise gr.Error("An error was encountered, please check your inputs and traceback.")

def toggle_gpu_split(gpu_split_auto):
    if gpu_split_auto:
        return gr.Textbox(value=None, visible=False)
    else:
        return gr.Textbox(visible=True)

def return_none():
    # Stupid workaround for "Number" components being unable to default to None
    return None

with gr.Blocks(title="TabbyAPI Gradio Loader") as webui:
    # Setup UI elements
    gr.Markdown(
    """
    # TabbyAPI Gradio Loader
    """)
    current_model = gr.Textbox(label="Current Model:")
    current_loras = gr.Textbox(label="Current Loras:")

    with gr.Tab("Connect to API"):
        connect_btn = gr.Button(value="Connect", variant="primary")
        api_url = gr.Textbox(value="http://127.0.0.1:5000", label="TabbyAPI Endpoint URL:", interactive=True)
        admin_key = gr.Textbox(label="Admin Key:", type="password", interactive=True)
        model_list = gr.Textbox(label="Available Models:", visible=False)
        draft_model_list = gr.Textbox(label="Available Draft Models:", visible=False)
        lora_list = gr.Textbox(label="Available Loras:", visible=False)

    with gr.Tab("Load Model"):
        with gr.Row():
            load_model_btn = gr.Button(value="Load Model", variant="primary")
            unload_model_btn = gr.Button(value="Unload Model", variant="stop")

        with gr.Accordion(open=False, label="Presets"):
            with gr.Row():
                load_preset = gr.Dropdown(choices=get_preset_list(True), label="Load Preset:", interactive=True)
                save_preset = gr.Textbox(label="Save Preset:", interactive=True)
            
            with gr.Row():
                load_preset_btn = gr.Button(value="Load Preset", variant="primary")
                del_preset_btn = gr.Button(value="Delete Preset", variant="stop")
                save_preset_btn = gr.Button(value="Save Preset", variant="primary")
                refresh_preset_btn = gr.Button(value="Refresh Presets")
            
        with gr.Group():
            models_drop = gr.Dropdown(label="Select Model:", interactive=True)
            with gr.Row():
                max_seq_len = gr.Number(value=return_none, label="Max Sequence Length:", precision=0, minimum=1, interactive=True)
                override_base_seq_len = gr.Number(value=return_none, label="Override Base Sequence Length (used to override value in config.json for auto-ROPE scaling):", precision=0, minimum=1, interactive=True)
            
            with gr.Row():
                model_rope_scale = gr.Number(value=return_none, label="Rope Scale:", minimum=1, interactive=True)
                model_rope_alpha = gr.Number(value=return_none, label="Rope Alpha:", minimum=1, interactive=True)

        with gr.Accordion(open=False, label="Speculative Decoding"):
            draft_models_drop = gr.Dropdown(label="Select Draft Model:", interactive=True)
            with gr.Row():
                draft_rope_scale = gr.Number(value=return_none, label="Draft Rope Scale:", minimum=1, interactive=True)
                draft_rope_alpha = gr.Number(value=return_none, label="Draft Rope Alpha:", minimum=1, interactive=True)
        
        with gr.Group():
            with gr.Row():
                cache_mode = gr.Radio(value="FP16", label="Cache Mode:", choices=["FP8","FP16"], interactive=True)
                no_flash_attention = gr.Checkbox(label="No Flash Attention", interactive=True)
                gpu_split_auto = gr.Checkbox(value=True, label="GPU Split Auto", interactive=True)

            gpu_split = gr.Textbox(label="GPU Split:", placeholder="List of integers separated by commas", visible=False, interactive=True)
            num_experts_per_token = gr.Number(value=return_none, label="Number of experts per token (MoE only):", precision=0, minimum=1, interactive=True)
            prompt_template = gr.Textbox(label="Prompt Template:", interactive=True)

    with gr.Tab("Load Loras"):
        with gr.Row():
            load_loras_btn = gr.Button(value="Load Loras", variant="primary")
            unload_loras_btn = gr.Button(value="Unload All Loras", variant="stop")
            
        loras_drop = gr.Dropdown(label="Select Loras:", choices=loras, multiselect=True, interactive=True)
        loras_table = gr.List(label="Lora Scaling:", visible=False, datatype="number", type="array", interactive=True)

    # Define event listeners
    # Connection tab
    connect_btn.click(fn=connect, inputs={api_url,admin_key}, outputs=[model_list, draft_model_list, lora_list, models_drop, draft_models_drop, loras_drop, current_model, current_loras])

    # Model tab
    load_preset_btn.click(fn=read_preset, inputs=load_preset, outputs=[models_drop, max_seq_len, override_base_seq_len, gpu_split_auto, gpu_split, model_rope_scale, model_rope_alpha, no_flash_attention, cache_mode, prompt_template, num_experts_per_token, draft_models_drop, draft_rope_scale, draft_rope_alpha])
    del_preset_btn.click(fn=del_preset, inputs=load_preset, outputs=load_preset)
    save_preset_btn.click(fn=write_preset, inputs=[save_preset, models_drop, max_seq_len, override_base_seq_len, gpu_split_auto, gpu_split, model_rope_scale, model_rope_alpha, no_flash_attention, cache_mode, prompt_template, num_experts_per_token, draft_models_drop, draft_rope_scale, draft_rope_alpha], outputs=[save_preset, load_preset])
    refresh_preset_btn.click(fn=get_preset_list, outputs=load_preset)

    gpu_split_auto.change(fn=toggle_gpu_split, inputs=gpu_split_auto, outputs=gpu_split)
    unload_model_btn.click(fn=unload_model, outputs=[current_model, current_loras])
    load_model_btn.click(fn=load_model, inputs=[models_drop, max_seq_len, override_base_seq_len, gpu_split_auto, gpu_split, model_rope_scale, model_rope_alpha, no_flash_attention, cache_mode, prompt_template, num_experts_per_token, draft_models_drop, draft_rope_scale, draft_rope_alpha], outputs=[current_model, current_loras])

    # Loras tab
    loras_drop.change(update_loras_table, inputs=loras_drop, outputs=loras_table)
    unload_loras_btn.click(fn=unload_loras, outputs=[current_model, current_loras])
    load_loras_btn.click(fn=load_loras, inputs=[loras_drop, loras_table], outputs=[current_model, current_loras])

webui.launch(show_api=False, server_name=host_url, server_port=args.port, share=args.share)