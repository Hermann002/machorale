from abc import ABC, abstractmethod

class IContribution(ABC):
    @property
    @abstractmethod
    def montant_par_mois(self):
        pass

    @property
    @abstractmethod
    def cible(self):
        pass

class IMembreContribution(ABC):
    @property
    @abstractmethod
    def membre(self):
        pass

    @property
    @abstractmethod
    def montant(self):
        pass