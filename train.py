import torch
import numpy as np
from loguru import logger
from torch import nn, optim


def train_recommender(args, model, train_dataloader, test_dataloader, path, results_file_path):
    optimizer = optim.Adam(model.parameters(), lr=args.lr_ft)

    for epoch in range(args.epoch):
        model.train()
        total_loss = 0

        logger.info(f'[Recommendation epoch {str(epoch)}]')
        logger.info('[Train]')

        for batch in train_dataloader.get_rec_data(args.batch_size):
            context_entities, context_tokens, plot, plot_mask, review, review_mask, target_items = batch
            scores_ft = model.forward(context_entities, context_tokens)
            loss_ft = model.criterion(scores_ft, target_items.to(args.device_id))

            loss_pt = model.pre_forward(plot, plot_mask, review, review_mask, target_items)
            # loss_pt = model.criterion(scores_pt, target_items.to(args.device_id))

            loss = loss_ft + (loss_pt * args.loss_lambda)
            total_loss += loss.data.float()
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
        print('Loss:\t%.4f' % total_loss)

        model.eval()
        topk = [1, 5, 10, 20, 50]
        hit = [[], [], [], [], []]

        for batch in test_dataloader.get_rec_data(args.batch_size, shuffle=False):
            context_entities, context_tokens, plot, plot_mask, review, review_mask, target_items = batch
            scores = model.forward(context_entities, context_tokens)

            # Item에 해당하는 것만 score 추출 (실험: 학습할 때도 똑같이 해줘야 할 지?)
            scores = scores[:, torch.LongTensor(model.movie2ids)]
            target_item = target_item.cpu().numpy()

            for k in range(len(topk)):
                sub_scores = scores.topk(topk[k])[1]
                sub_scores = sub_scores.cpu().numpy()

                for (label, score) in zip(target_item, sub_scores):
                    target_idx = model.movie2ids.index(label)
                    hit[k].append(np.isin(target_idx, score))

        print('Epoch %d : test done' % (epoch + 1))

        for k in range(len(topk)):
            hit_score = np.mean(hit[k])
            print('hit@%d:\t%.4f' % (topk[k], hit_score))

        with open(results_file_path, 'a', encoding='utf-8') as result_f:
            result_f.write('Epoch:\t%d\t Loss:\t%.2f\tH@1\t%.4f\tH@5\t%.4f\tH@10\t%.4f\tH@20\t%.4f\tH@50\t%.4f\n' % (
                epoch + 1, total_loss, np.mean(hit[0]), np.mean(hit[1]), np.mean(hit[2]), np.mean(hit[3]), np.mean(hit[4])))

    torch.save(model.state_dict(), path)  # TIME_MODELNAME 형식

# todo: train_generator
