import argparse
import logging
import os

def parse_args():
    parser = argparse.ArgumentParser()
    # common
    parser.add_argument('--name', type=str,
                        default='plot-review-serial-none')
    parser.add_argument('--max_dialog_len', type=int, default=128)  # 50, 100, 150, 200, 250, (300)
    parser.add_argument('--kg_emb_dim', type=int, default=128)
    parser.add_argument('--num_bases', type=int, default=8)
    parser.add_argument('--head_num', type=int, default=8)
    parser.add_argument('--task', type=str, default='rec')
    parser.add_argument('--num_trial', type=int, default=3)
    parser.add_argument('--device_id', type=int, default=0)
    parser.add_argument('--mode', type=str, default='test', choices=['valid','test'])
    parser.add_argument('--dataset_path', type=str, default='data/redial', choices=['data/redial', 'data/inspired', 'data/DuRecDial'])

    # rec
    parser.add_argument('--n_review', type=int, default=9)
    parser.add_argument('--n_meta', type=int, default=5)
    # parser.add_argument('--meta', type=str, default='word',
    #                     choices=['meta', 'word', 'meta-word'])  # [NEW] choice among three candidates
    parser.add_argument('--n_sample', type=int, default=1, help='sampling')
    parser.add_argument('--max_review_len', type=int, default=128)  # 50, 100, 150, 200, 250, (300)
    parser.add_argument('--epoch_pt', type=int, default=30)  # [NEW] # epochs of pre-training
    parser.add_argument('--epoch_ft', type=int, default=10)  # [NEW] # epochs if fine-tuning
    parser.add_argument('--batch_size', type=int, default=2)
    parser.add_argument('--lr_pt', type=float, default=1e-4, help='Pre-training Learning rate')
    parser.add_argument('--lr_ft', type=float, default=1e-3, help='Fine-tuning Learning rate')
    parser.add_argument('--loss_lambda', type=float, default=0.1, help='lambda')
    parser.add_argument('--position', action='store_false')  # [NEW] default: use the positional embedding
    parser.add_argument('--dropout_pt', type=float, default=0, help='dropout_pt')  # [NEW] dropout in pre-training
    parser.add_argument('--dropout_ft', type=float, default=0, help='dropout_ft')  # [NEW] dropout in fine-tuning
    parser.add_argument('--lr_dc_step', type=int, default=5, help='warmup_step')
    parser.add_argument('--lr_dc', type=float, default=0.1, help='warmup_gamma')
    parser.add_argument('--pretrained', action='store_true')
    parser.add_argument('--debug', action='store_true')
    parser.add_argument('--model', type=str, default='LATTE')

    # conv
    parser.add_argument('--n_template_sample', type=int, default=2, help='sampling')
    parser.add_argument('--conv_epoch_pt', type=int, default=10)  # [NEW] # epochs of pre-training
    parser.add_argument('--conv_epoch_ft', type=int, default=10)  # [NEW] # epochs if fine-tuning
    parser.add_argument('--conv_batch_size', type=int, default=2)
    parser.add_argument('--gen_batch_size', type=int, default=1)
    parser.add_argument('--conv_lr_pt', type=float, default=1e-4, help='Pre-training Learning rate')
    parser.add_argument('--conv_lr_ft', type=float, default=1e-4, help='Fine-tuning Learning rate')
    parser.add_argument('--context_max_length', type=int, default=128)
    parser.add_argument("--max_gen_len", type=int, default=128)
    parser.add_argument("--max_title_len", type=int, default=40)
    parser.add_argument("--entity_max_length", type=int, help="max entity length in dataset.", default=32)
    parser.add_argument('--num_warmup_steps', type=int, default=6345)
    parser.add_argument("--weight_decay", type=float, default=0.01, help="Weight decay to use.")
    parser.add_argument('--conv_loss_lambda', type=float, default=0.1, help='conv lambda')
    parser.add_argument("--conv_pre_eval_batch_size", type=int, default=2, help="conv pre-training eval batch size")
    parser.add_argument('--conv_pretrained', action='store_true')
    # parser.add_argument('--conv_pretrained_path', default='none', type=str)
    # parser.add_argument('--conv_pretrained_type', default='none', type=str)

    # GPT
    parser.add_argument('--gpt_name', type=str, default='gpt2',
                        choices=['microsoft/DialoGPT-small', 'microsoft/DialoGPT-large', 'gpt2', 'gpt2-large',
                                 'facebook/bart-base'])
    parser.add_argument('--gpt_n_layer', type=int, default=-1)

    # BERT
    parser.add_argument('--bert_name', type=str, default='bert-base-uncased',
                        choices=['bert-base-uncased', 'albert-base-v2', 'prajjwal1/bert-small',
                                 'prajjwal1/bert-mini', 'prajjwal1/bert-tiny', 'roberta-base', 'facebook/bart-base',
                                 'microsoft/DialoGPT-small',
                                 'bert-large-uncased', 't5-base'])  # [NEW] add roberta
    parser.add_argument('--n_layer', type=int, default=2)
    parser.add_argument('--t_layer', type=int, default=-1)

    # TransformerEncoder Args
    parser.add_argument('--n_heads', type=int, default=2, help='n_heads')
    parser.add_argument('--n_layers', type=int, default=2, help='n_layers')
    parser.add_argument('--dropout', type=float, default=0.1, help='dropout')
    parser.add_argument('--attention_dropout', type=float, default=0.0, help='attention_dropout')
    parser.add_argument('--relu_dropout', type=float, default=0.1, help='relu_dropout')
    parser.add_argument('--learn_positional_embeddings', type=bool, default=False, help='learn_positional_embeddings')
    parser.add_argument('--embeddings_scale', type=bool, default=True, help='embeddings_scale')
    parser.add_argument('--ffn_size', type=int, default=300, help='ffn_size')
    parser.add_argument('--reduction', type=bool, default=False, help='reduction')
    parser.add_argument('--n_positions', type=int, default=1024, help='n_positions')
    parser.add_argument('--pad_token_id', type=int, default=0, help='pad_token_id')
    parser.add_argument('--vocab_size', type=int, default=30522, help='vocab_size')

    args = parser.parse_args()
    args.home = os.path.dirname(__file__)
    print(args.home)
    logging.info(args)
    return args


# main
if __name__ == "__main__":
    args = parse_args()
