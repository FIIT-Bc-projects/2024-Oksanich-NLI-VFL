from typing import Dict

from flwr.common import NDArrays, Scalar, Context
from flwr.client import NumPyClient, ClientApp

from sentiment_analysis.task import Transformer, get_weights, set_weights, train, test, load_data

from transformers import AutoModel

import torch


class FlowerClient(NumPyClient):
    def __init__(self, model, training_loader, validation_loader) -> None:
        super().__init__()

        self.training_loader = training_loader
        self.validation_loader = validation_loader

        self.model: Transformer = model

        self.criterion = torch.nn.CrossEntropyLoss()
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

        self.model = self.model.to(self.device)
        self.criterion = self.criterion.to(self.device)

    def fit(self, parameters, config):
        set_weights(self.model, parameters)

        optimizer = torch.optim.Adam(self.model.parameters(), lr=1e-5)

        loss, accuracy = train(self.model, self.training_loader, self.device, self.criterion, optimizer)

        return get_weights(self.model), len(self.training_loader), {"loss": loss, "accuracy": accuracy}

    def evaluate(self, parameters: NDArrays, config: Dict[str, Scalar]):
        set_weights(self.model, parameters)

        loss, accuracy = test(self.model, self.validation_loader, self.device, self.criterion)

        return float(loss), len(self.validation_loader), {"accuracy": accuracy}


def client_fn(context: Context):
    # Load model and data
    tf = AutoModel.from_pretrained("bert-base-uncased")
    model = Transformer(tf, num_classes=3, freeze=False)

    partition_id = context.node_config["partition-id"]
    num_partitions = context.node_config["num-partitions"]

    training_loader, validation_loader = load_data(partition_id, num_partitions)

    return FlowerClient(model, training_loader, validation_loader).to_client()


app = ClientApp(
    client_fn,
)