import torch
import numpy as np
#import gradio as gr
from PIL import Image
from omegaconf import OmegaConf
from pathlib import Path
from vocoder.bigvgan.models import VocoderBigVGAN
from ldm.models.diffusion.ddim import DDIMSampler
from ldm.util import instantiate_from_config
from wav_evaluation.models.CLAPWrapper import CLAPWrapper
from ldm.models.diffusion.ddpm_audio import LatentDiffusion_audio, LatentFinetuneDiffusion
from scipy.io.wavfile import write
import tempfile
import os


SAMPLE_RATE = 16000

torch.set_grad_enabled(False)
device = torch.device("cuda") if torch.cuda.is_available() else torch.device("cpu")

def dur_to_size(duration):
    latent_width = int(duration * 7.8)
    if latent_width % 4 != 0:
        latent_width = (latent_width // 4 + 1) * 4
    return latent_width

def initialize_model(config, ckpt):
    config = OmegaConf.load(config)
    model = LatentDiffusion_audio(**config.model.get("params", dict()))#instantiate_from_config(config.model)
    model.load_state_dict(torch.load(ckpt,map_location='cpu')["state_dict"], strict=False)

    model = model.to(device)
    model.cond_stage_model.to(model.device)
    model.cond_stage_model.device = model.device
    print(model.device,device,model.cond_stage_model.device)
    sampler = DDIMSampler(model)

    return sampler

sampler = initialize_model('configs/text_to_audio/txt2audio_args.yaml', 'useful_ckpts/maa1_full.ckpt')
vocoder = VocoderBigVGAN('vocoder/logs/bigvnat',device=device)
clap_model = CLAPWrapper('useful_ckpts/CLAP/CLAP_weights_2022.pth','useful_ckpts/CLAP/config.yml',use_cuda=torch.cuda.is_available())

def select_best_audio(prompt, wav_list, duration):
    text_embeddings = clap_model.get_text_embeddings([prompt])
    score_list = []
    for data in wav_list:
        sr,wav = data
        audio_embeddings = clap_model.get_audio_embeddings([(torch.FloatTensor(wav),sr)], resample=True, duration=duration)
        score = clap_model.compute_similarity(audio_embeddings, text_embeddings,use_logit_scale=False).squeeze().cpu().numpy()
        score_list.append(score)
    max_index = np.array(score_list).argmax()
    print(score_list,max_index)
    return wav_list[max_index]

def txt2audio(sampler, vocoder, prompt, seed, scale, ddim_steps, n_samples=1, H=80, duration=9):
    prng = np.random.RandomState(seed)
    
    W = dur_to_size(duration) * 8

    start_code = prng.randn(n_samples, sampler.model.first_stage_model.embed_dim, H // 8, W // 8)
    start_code = torch.from_numpy(start_code).to(device=device, dtype=torch.float32)
    
    uc = None
    if scale != 1.0:
        uc = sampler.model.get_learned_conditioning(n_samples * [""])
    c = sampler.model.get_learned_conditioning(n_samples * [prompt])# shape:[1,77,1280],即还没有变成句子embedding，仍是每个单词的embedding
    shape = [sampler.model.first_stage_model.embed_dim, H//8, W//8]  # (z_dim, 80//2^x, 848//2^x)
    samples_ddim, _ = sampler.sample(S=ddim_steps,
                                        conditioning=c,
                                        batch_size=n_samples,
                                        shape=shape,
                                        verbose=False,
                                        unconditional_guidance_scale=scale,
                                        unconditional_conditioning=uc,
                                        x_T=start_code)

    x_samples_ddim = sampler.model.decode_first_stage(samples_ddim)

    print("Select best")

    wav_list = []
    for idx,spec in enumerate(x_samples_ddim):
        wav = vocoder.vocode(spec)
        wav_list.append((SAMPLE_RATE,wav))
    best_wav = select_best_audio(prompt, wav_list, duration)

    return best_wav


def predict(prompt, duration, ddim_steps, num_samples, scale, seed):
    melbins = 80
    with torch.no_grad():
        result = txt2audio(
            sampler=sampler,
            vocoder=vocoder,
            prompt=prompt,
            seed=seed,
            scale=scale,
            ddim_steps=ddim_steps,
            n_samples=num_samples,
            H=melbins,
            duration=duration
        )

    return result

def save_audio(audio, path, sr):
    MAX_WAV_VALUE = 32768.0
    # wav: torch with 1d shape
    audio = audio * MAX_WAV_VALUE
    audio = audio.astype('int16')
    write(path, sr, audio)


def sound_predict(prompt, duration):

    GENERATION_EXAMPLES = 5 #5 samples of generation

    sr, wav = predict(prompt, duration, GENERATION_EXAMPLES, 3, 3, 55)

    path = os.path.join(tempfile.mkdtemp(), 'audio.wav')

    save_audio(wav, path, sr)

    #path = "C:/Users/Sover/Desktop/sound/goblin-cackle.wav"

    sound_file = open(path, mode='rb')
    sound_data = sound_file.read()
    sound_file.close()

    #os.remove(path)

    return sound_data

