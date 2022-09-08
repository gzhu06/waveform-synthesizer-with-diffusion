# Copyright 2020 LMNT, Inc. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================

import numpy as np
import os
import torch
import torchaudio

from argparse import ArgumentParser

from diffwave.params import AttrDict, params as base_params
from diffwave.model import DiffWave

def diffusion_paramters(params):
    
    training_noise_schedule = np.array(params.noise_schedule)
    inference_noise_schedule = training_noise_schedule
    
    beta = torch.from_numpy(inference_noise_schedule)
    alpha = 1 - beta
    
    alpha_bar = alpha + 0
    beta_tilde = beta + 0
    for t in range(1, len(training_noise_schedule)):
        alpha_bar[t] *= alpha_bar[t-1]
        beta_tilde[t] *= (1-alpha_bar[t-1])/(1-alpha_bar[t]) 
        
    sigma = torch.sqrt(beta_tilde)
    return alpha, alpha_bar, beta_tilde, sigma
        
def predict(model_dir=None, params=None, 
            device=torch.device('cuda')):
    checkpoint = torch.load(os.path.join(model_dir, 'weights-63104.pt'))
    model = DiffWave(AttrDict(base_params)).to(device)
    model.load_state_dict(checkpoint['model'])
    model.eval()
    
    alpha, alpha_bar, beta_tilda, sigma = diffusion_paramters(model.params)
    with torch.no_grad():
    
        # audio initialization
        audio = torch.randn(1, params.audio_len, device=device)
        for t in range(len(alpha_bar)-1, -1, -1):

            epsilon_theta = model(audio, torch.tensor([t], device=audio.device)).squeeze(1)
            audio = (audio-(1-alpha[t])/torch.sqrt(1-alpha_bar[t])*epsilon_theta)/torch.sqrt(alpha[t]) 

            if t > 0:
                noise = torch.randn_like(audio)
                audio = audio + sigma[t] * noise
                
    return audio

def main(args):
    audio, sr = predict(model_dir=args.model_dir, 
                        params=base_params)
    torchaudio.save(args.output, audio.cpu(), sample_rate=sr)

if __name__ == '__main__':
    parser = ArgumentParser(description='runs inference on a spectrogram file generated by diffwave.preprocess')
    parser.add_argument('model_dir', help='directory containing a trained model (or full path to weights.pt file)')
    parser.add_argument('--output', '-o', default='output.wav',
                        help='output file name')
    main(parser.parse_args())
