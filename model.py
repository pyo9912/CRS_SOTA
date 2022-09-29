import torch.nn.functional as F
from torch import nn
import torch
from layers import AdditiveAttention, SelfDotAttention
from torch_geometric.nn import RGCNConv
from torch.nn import TransformerEncoder, TransformerEncoderLayer
from utils import edge_to_pyg_format


class MovieExpertCRS(nn.Module):
    def __init__(self, args, bert_model, token_emb_dim, movie2ids, entity_kg, n_entity, name):
        super(MovieExpertCRS, self).__init__()

        # Setting
        self.args = args
        self.movie2ids = movie2ids
        self.name = name  # argument 를 통한 abaltion을 위해 필요
        self.device_id = args.device_id

        # R-GCN
        # todo: pre-trainig (R-GCN 자체 or content 내 meta data 를 활용하여?) (후자가 날 듯)
        self.n_entity = n_entity
        self.num_bases = args.num_bases
        self.kg_emb_dim = args.kg_emb_dim
        self.n_relation = entity_kg['n_relation']
        self.kg_encoder = RGCNConv(self.n_entity, self.kg_emb_dim, self.n_relation, num_bases=self.num_bases)
        self.edge_idx, self.edge_type = edge_to_pyg_format(entity_kg['edge'], 'RGCN')
        self.edge_idx = self.edge_idx.to(self.device_id)
        self.edge_type = self.edge_type.to(self.device_id)
        self.pad_entity_idx = 0

        self.entity_attention = SelfDotAttention(self.kg_emb_dim, self.kg_emb_dim)
        # Dialog
        self.token_emb_dim = token_emb_dim
        self.word_encoder = bert_model  # bert or transformer
        # self.encoder_layer = nn.TransformerEncoderLayer(d_model=self.token_emb_dim, n_head=8)
        # self.word_encoder = nn.TransformerEncoder(encoder_layer=self.encoder_layer, num_layers=6)

        self.token_attention = AdditiveAttention(self.token_emb_dim, self.token_emb_dim)
        self.linear_transformation = nn.Linear(self.token_emb_dim, self.kg_emb_dim)

        # Gating
        self.gating = nn.Linear(2 * self.kg_emb_dim, self.kg_emb_dim)

        # Prediction
        # self.linear_output = nn.Linear(self.token_emb_dim, self.num_movies)

        # Loss
        self.criterion = nn.CrossEntropyLoss()

        # initialize all parameter (except for pretrained BERT)
        self.initialize()

    # todo: initialize 해줘야 할 parameter check
    def initialize(self):
        # nn.init.xavier_uniform_(self.linear_output.weight)
        nn.init.xavier_uniform_(self.linear_transformation.weight)
        nn.init.xavier_uniform_(self.gating.weight)

        self.entity_attention.initialize()
        self.token_attention.initialize()

    # Input # todo: meta information (entitiy)도 같이 입력
    # plot_token    :   [batch_size, n_plot, max_plot_len]
    # review_token    :   [batch_size, n_review, max_review_len]
    # target_item   :   [batch_size]
    def pre_forward(self, plot_token, plot_mask, review_token, review_mask, target_item, compute_score=False):
        # text = torch.cat([meta_token, plot_token], dim=1)
        # mask = torch.cat([meta_mask, plot_mask], dim=1)
        batch_size = plot_token.shape[0]
        n_plot = plot_token.shape[1]
        max_plot_len = plot_token.shape[2]
        n_review = review_token.shape[1]
        max_review_len = review_token.shape[2]

        if 'plot' in self.name and 'review' in self.name:
            if 'serial' in self.name:  # Cand.3: Review | Plot
                # p_mask = torch.sum(plot_mask, dim=1, keepdim=True) > 0
                # text = p_mask * plot_token + (~p_mask) * review_token
                # mask = p_mask * plot_mask + (~p_mask) * review_mask
                text = torch.cat([plot_token, review_token], dim=1)  # [B, 2N, L]
                mask = torch.cat([plot_mask, review_mask], dim=1)  # [B, 2N, L]
                max_len = max_plot_len
                n_text = n_plot * 2

            else:  # Cand.4: Review & Plot
                text = torch.cat([plot_token, review_token], dim=1)
                mask = torch.cat([plot_mask, review_mask], dim=1)
        elif 'plot' in self.name:  # cand.1: Plot
            text = plot_token
            mask = plot_mask
            max_len = max_plot_len
            n_text = n_plot

        elif 'review' in self.name:  # Cand.2: Review
            text = review_token
            mask = review_mask
            max_len = max_plot_len
            n_text = n_plot
        text = text.to(self.device_id)
        mask = mask.to(self.device_id)

        # [1, B] -> [N, B] -> [N X B]
        target_item = target_item.unsqueeze(1).repeat(1, n_text).view(-1).to(self.device_id)
        # todo: entitiy 활용해서 pre-train
        # code
        # text: [B * N, L]
        text = text.view(-1, max_len)
        mask = mask.view(-1, max_len)
        text_emb = self.word_encoder(input_ids=text,
                                     attention_mask=mask).last_hidden_state  # [B, L, d] -> [B * N, L, d]
        content_emb = self.token_attention(text_emb, mask)  # [B, d] -> [B * N, d]
        content_emb = self.linear_transformation(content_emb)  # [B * N, d']

        # todo: MLP layer 로 할 지 dot-prodcut 으로 할 지? (실험)
        # scores = self.linear_output(content_emb)  # [B, V]
        kg_embedding = self.kg_encoder(None, self.edge_idx, self.edge_type)  # [E, d']
        scores = F.linear(content_emb, kg_embedding)  # [B * N, E]
        loss = self.criterion(scores, target_item)
        if compute_score:
            return scores, target_item
        return loss

    def forward(self, context_entities, context_tokens):

        kg_embedding = self.kg_encoder(None, self.edge_idx, self.edge_type)  # (n_entity, entity_dim)
        entity_representations = kg_embedding[context_entities]  # [bs, context_len, entity_dim]
        entity_padding_mask = ~context_entities.eq(self.pad_entity_idx).to(self.device_id)  # (bs, entity_len)
        entity_attn_rep = self.entity_attention(entity_representations, entity_padding_mask)  # (bs, entity_dim)

        token_padding_mask = ~context_tokens.eq(self.pad_entity_idx).to(self.device_id)  # (bs, token_len)
        token_embedding = self.word_encoder(input_ids=context_tokens.to(self.device_id),
                                            attention_mask=token_padding_mask.to(
                                                self.device_id)).last_hidden_state  # [bs, token_len, word_dim]
        token_attn_rep = self.token_attention(token_embedding, token_padding_mask)  # [bs, word_dim]

        # todo: Linear transformation을 꼭 해줘야 하는지? 해준다면 word 단에서 할 지 sentence 단에서 할 지
        token_attn_rep = self.linear_transformation(token_attn_rep)

        # 22.09.24 Gating mechanism 없이 word 로만 training -->  주석 해제
        gate = torch.sigmoid(self.gating(torch.cat([token_attn_rep, entity_attn_rep], dim=1)))
        user_embedding = gate * token_attn_rep + (1 - gate) * entity_attn_rep
        # user_embedding = token_attn_rep
        scores = F.linear(user_embedding, kg_embedding)
        return scores
