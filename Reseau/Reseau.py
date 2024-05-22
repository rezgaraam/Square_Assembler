import os, string, sys, time, getopt

#sys.path.append("C:\ivy-python-2.1")
from ivy.std_api import *
import time


class Reseau:
    """Classe pour la gestion du réseau entre les deux joueurs:
        - Initialisation de la connexion
        - Envoi de message
        - Réception de message
        - Gestion des informations
    """
    def __init__(self, fenetre, nom):
        self.fenetre = fenetre
        self.nom = nom
        self.nomAdversaire = None
        self.temps = None
        # adresse et port du serveur Ivy (par défaut=localhost)
        self.adresse = "127.0.0.1"
        self.port = "2010"
        self.message = ""
        self.connexion2joueurs = False
        self.estServeur = None
        self.infoNom = False
        self.infoDuree = False
        self.infoTaille = False
        self.infoPlateau = False
        self.dureeTour = 0
        self.taille = 0
        self.map = []
        self.passerTour = False

    def on_msg(self, agent, *arg):
        """Méthode pour gérer les messages reçus"""
        # print('Received from %r: %s', agent, arg and str(arg) or '<no args>')
        if (self.connexion2joueurs):
            self.message = str(arg)
        if ("is ready" in str(arg)):
            self.connexion2joueurs = True
            test1 = str(arg)
            test2 = test1.split(' ')
            test3 = test2[1]
            self.nomAdversaire = str(test3)
            self.infoNom = True
            self.envoyer("time: " + str(self.temps) + " ")
        # Qui est le serveur
        if ("time:" in str(arg)):
            if (self.connexion2joueurs):
                test1 = str(arg)
                test2 = test1.split(' ')
                test3 = test2[1]
                test4 = float(test3)
                if (test4 < self.temps):
                    self.estServeur = False
                else:
                    self.estServeur = True
                self.fenetre.connexionReussi()
        # INFOS
        # Pour récupérer la durée d'un tour
        if ("tour:" in str(arg)):
            test1 = str(arg)
            test2 = test1.split(' ')
            test3 = test2[1]
            test4 = int(test3)
            self.dureeTour = test4
            self.infoDuree = True
        # Pour récupérer la taille de la map
        if ("taille:" in str(arg)):
            test1 = str(arg)
            test2 = test1.split(' ')
            test3 = test2[1]
            test4 = int(test3)
            self.taille = test4
            self.infoTaille = True
        if ("map:" in str(arg)):
            test1 = str(arg)
            test2 = test1.replace("map:", "").replace("[", "").replace("]", "").replace("'", "").replace("(", "")
            test2 = test2.split(',')
            self.map = []
            i = 0
            while (i < self.taille * self.taille):
                self.map.append(int(test2[i]))
                i += 1
            self.infoPlateau = True
        if ("Infos ok" in str(arg)):
            self.fenetre.chargementInformations()
        if ("click:" in str(arg)):
            test1 = str(arg)
            test2 = test1.split(' ')
            self.fenetre.cliqueReseau(int(test2[1]), int(test2[2]))
        if ("passer tour" in str(arg)):
            self.fenetre.changementTour()
        if ("nouvelle partie" in str(arg)):
            self.fenetre.demandeNouvellePartie()

    def aInformation(self):
        """Méthode boolean pour vérifier si on a toutes les informations nécessaires pour commencer la partie"""
        return self.infoDuree and self.infoTaille and self.infoPlateau and self.infoNom

    def on_connection_change(self, agent, event):
        """Méthode pour gérer les événements de connexion"""
        if event == IvyApplicationDisconnected:
            self.connexion2joueurs = False
            self.fenetre.deconnexion()

    def on_die(self):
        """Méthode pour arrêter le bus Ivy"""
        IvyStop()

    def envoyer(self, message):
        """Méthode pour envoyer un message à l'autre joueur"""
        IvySendMsg(message)

    def initialisation(self):
        """ méthode qui permet d'initialiser bus ivy """
        readymsg = ' ' + self.nom + ' is ready '
        IvyInit(self.nom, readymsg, 0, self.on_connection_change, self.on_die)
        # bind the supplied regexps
        IvyBindMsg(self.on_msg, "(.*)")

    def connexion(self):
        """Méthode pour se connecter à un serveur Ivy avec initialisation du temps"""
        self.temps = time.time()
        # starting the bus
        IvyStart(self.adresse + ":" + self.port)