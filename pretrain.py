import torch
import numpy as np
from loguru import logger
from torch import nn, optim
from tqdm import tqdm


def pretrain(args, model, pretrain_dataloader, path):
    optimizer = optim.Adam(model.parameters(), lr=args.lr_pt)

    for epoch in range(args.epoch_pt):
        model.train()
        total_loss = 0
        total_loss_lm = 0
        for movie_id, plot_meta, plot_token, plot_mask, review_meta, review_token, review_mask, mask_label in tqdm(
                pretrain_dataloader, bar_format=' {percentage:3.0f} % | {bar:23} {r_bar}'):
            loss, masked_lm_loss = model.pre_forward(plot_meta, plot_token, plot_mask, review_meta, review_token,
                                                     review_mask, movie_id,
                                                     mask_label)
            # scores = scores[:, torch.LongTensor(model.movie2ids)]
            # loss = model.criterion(scores, movie_id)
            joint_loss = loss + masked_lm_loss
            total_loss += loss.data.float()
            total_loss_lm += masked_lm_loss.data.float()
            optimizer.zero_grad()
            joint_loss.backward()
            optimizer.step()
        print('[Epoch%d]\tLoss:\t%.4f\tLoss_LM:\t%.4f' % (epoch, total_loss, total_loss_lm))

    torch.save(model.state_dict(), path)  # TIME_MODELNAME 형식

    model.eval()
    topk = [1, 5, 10, 20]
    hit = [[], [], [], []]

    for movie_id, plot_meta, plot_token, plot_mask, review_meta, review_token, review_mask, mask_label in tqdm(
            pretrain_dataloader, bar_format=' {percentage:3.0f} % | {bar:23} {r_bar}'):
        scores, target_id = model.pre_forward(plot_meta, plot_token, plot_mask, review_meta, review_token, review_mask,
                                              movie_id, mask_label,
                                              compute_score=True)
        scores = scores[:, torch.LongTensor(model.movie2ids)]

        # Item에 해당하는 것만 score 추출 (실험: 학습할 때도 똑같이 해줘야 할 지?)
        target_id = target_id.cpu().numpy()

        for k in range(len(topk)):
            sub_scores = scores.topk(topk[k])[1]
            sub_scores = sub_scores.cpu().numpy()

            for (label, score) in zip(target_id, sub_scores):
                y = model.movie2ids.index(label)
                hit[k].append(np.isin(y, score))

    print('Epoch %d : pre-train test done' % (epoch + 1))
    for k in range(len(topk)):
        hit_score = np.mean(hit[k])
        print('[pre-train] hit@%d:\t%.4f' % (topk[k], hit_score))
