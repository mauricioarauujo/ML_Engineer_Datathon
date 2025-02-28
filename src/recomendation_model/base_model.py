# src/recomendation_model/base_model.py
from abc import ABC, abstractmethod
import lightgbm as lgb
import numpy as np


class BaseRecommender(ABC):
    def __init__(self, params=None, num_boost_round=100):
        """
        Inicializa o modelo com parâmetros padrão ou personalizados para ranking.

        Args:
            params (dict, opcional): Parâmetros para o LightGBM. Caso não seja fornecido,
                                     utiliza um conjunto padrão voltado para ranking.
            num_boost_round (int, opcional): Número de iterações (árvores) no treinamento.
        """
        # Define os parâmetros padrão para ranking, incluindo label_gain para scores de 0 a 100
        default_params = {
            "objective": "lambdarank",  # Usando objetivo de ranking (LambdaRank)
            "metric": "ndcg",  # Métrica típica para avaliar ranking
            "learning_rate": 0.05,
            "num_leaves": 39,
            "verbose": -1,
            "label_gain": [
                2**i - 1 for i in range(101)
            ],  # Vetor de ganho para rótulos de 0 a 100
        }

        # Se o usuário passar parâmetros personalizados, verifica se label_gain não está definido
        if params is not None:
            if (
                params.get("objective", default_params["objective"]) == "lambdarank"
                and "label_gain" not in params
            ):
                params["label_gain"] = [2**i - 1 for i in range(101)]
            self.params = params
        else:
            self.params = default_params

        self.num_boost_round = num_boost_round
        self.model = None

    @abstractmethod
    def predict(self, model_input):
        """
        Realiza a predição.
        Este método é abstrato aqui, mas vamos ilustrar abaixo como pode ser implementado.

        Args:
            model_input (dict): Dicionário que deve conter as chaves
                                'client_features' e 'news_features'.
        """
        pass

    @abstractmethod
    def train(self, X, y):
        """
        Realiza o treinamento do modelo.
        Método abstrato para ser implementado.
        """
        pass


class LightGBMRanker(BaseRecommender):
    """
    Exemplo concreto de implementação de um modelo de ranking no LightGBM,
    utilizando o objetivo 'lambdarank' para aprendizado de ranking.
    """

    def __init__(self, params=None, num_boost_round=100):
        # Caso seja passado um dicionário de parâmetros que contenha 'num_class',
        # removemos para evitar conflitos com o objetivo de ranking.
        if params is not None and "num_class" in params:
            del params["num_class"]
        super().__init__(params=params, num_boost_round=num_boost_round)

    def train(self, X, y, group):
        """
        Treina o modelo LightGBM em modo de ranking (LambdaRank).

        Args:
            X (array-like): Features de todos os pares (usuário-notícia),
                            por exemplo [n_amostras x n_features].
            y (array-like): Alvo (score ou relevância) de cada par (usuário-notícia).
            group (list ou array): Quantidade de amostras (instâncias) para cada usuário
                                   ou grupo. A soma de todos os elementos de 'group'
                                   deve ser igual ao número total de linhas em X.
        """
        # Valida se a soma dos grupos bate com o número total de amostras
        if np.sum(group) != X.shape[0]:
            raise ValueError(
                "A soma dos valores em 'group' deve ser igual ao número de amostras em X."
            )

        # Cria Dataset para ranking, informando os grupos
        train_data = lgb.Dataset(X, label=y, group=group)

        # Treina o modelo com os parâmetros definidos
        self.model = lgb.train(self.params, train_data, num_boost_round=self.num_boost_round)

    def predict(self, model_input):
        """
        Realiza a predição (score) para ranqueamento.
        Recebe dicionário com client_features e news_features, concatena e roda predict.

        Args:
            model_input (dict): Deve conter:
                - 'client_features': array-like (n_samples x n_client_feats)
                - 'news_features': array-like (n_samples x n_news_feats)

        Returns:
            np.ndarray: Array com os scores preditos (quanto maior o score,
                        maior a relevância/rank).
        """
        client_features = model_input.get("client_features")
        news_features = model_input.get("news_features")

        if client_features is None or news_features is None:
            raise ValueError(
                "O dicionário 'model_input' deve conter as chaves "
                "'client_features' e 'news_features'."
            )

        # Combina as features do usuário e da notícia
        X = np.concatenate([client_features, news_features], axis=1)

        if self.model is None:
            raise ValueError(
                "O modelo ainda não foi treinado. Execute train() antes de predict()."
            )

        # Realiza a predição de scores (valores de relevância)
        scores = self.model.predict(X)

        return scores
