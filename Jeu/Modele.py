from Jeu import Plateau


class Modele:
    """ Classe définissant le modèle du jeu caractérisé par :
        - le score des joueurs
        - la liste de couleurs de chaque joueurs
        - le nombre de parties jouées
        - le nombre de joueurs
        - le plateau de jeu
        - la taille du plateau
        - le tour de jeu
      """
    def __init__(self, nbJoueur=0):
        #score des joueurs
        self.scoreJ1 = 0
        self.scoreJ2 = 0
        # Liste des couleurs du joueur 1 et 2 (pour le mode 2 joueurs)
        self.listeCouleurJ1 = []
        self.listeCouleurJ2 = []
        # Liste des couleurs restantes (les couleurs non attribuées aux joueurs 1 et 2 à l'instant t)
        self.listeCouleurRestante = []
        self.nombrePartie = 0
        # Nombre de joueurs pour initialiser mode de plateau (1 ou 2)
        self.nbJoueur = nbJoueur
        # Booléen pour savoir si une partie est en cours
        self.enJeu = False
        # Plateau de jeu
        self.plateau = None
        self.tailleX = 0
        self.tailleY = 0
        self.tourDeJeu = None

        self.joueurNumero = 0

    def existePlateau(self):
        """Méthode pour savoir si le plateau est initialisé ou non"""
        return (self.plateau != None)


    def estMaCouleur(self, couleur, joueur=1):
        """Méthode pour savoir quel joueur possède la couleur"""
        if (joueur == 1):
            return couleur in self.listeCouleurJ1 or (
                        couleur in self.listeCouleurRestante and len(self.listeCouleurJ1) < self.plateau.nbCouleur / 2)
        else:
            return couleur in self.listeCouleurJ2 or (
                        couleur in self.listeCouleurRestante and len(self.listeCouleurJ2) < self.plateau.nbCouleur / 2)


    def ajouterCouleurJ1(self, couleur):
        """Méthode pour ajouter une couleur au joueur 1"""
        if (len(self.listeCouleurJ1) < self.plateau.nbCouleur / 2):
            if (couleur in self.listeCouleurRestante):
                self.listeCouleurJ1.append(couleur)
                self.listeCouleurRestante.remove(couleur)

    def ajouterCouleurJ2(self, couleur):
        """Méthode pour ajouter une couleur au joueur 2"""
        if (len(self.listeCouleurJ2) < self.plateau.nbCouleur / 2):
            if (couleur in self.listeCouleurRestante):
                self.listeCouleurJ2.append(couleur)
                self.listeCouleurRestante.remove(couleur)

    def supprimerCase(self, x, y, joueur=1):
        """Méthode pour supprimer une case du plateau"""
        couleur = self.plateau.getCouleur(x, y) # Récupération de la couleur de la case à supprimer (x, y)
        if (couleur == "white"):
            return False
        else:
            caseSupprime = False
            if (joueur == 1):
                if (self.nbJoueur == 1):
                    scoreTmp = self.plateau.supprime(x, y)
                    if (scoreTmp != 0):
                        self.scoreJ1 += scoreTmp
                        caseSupprime = True
                else:
                    # 2 joueurs, donc on prend en compte la couleur
                    if (self.estMaCouleur(couleur, 1)):
                        scoreTmp = self.plateau.supprime(x, y)

                        if (scoreTmp != 0):
                            self.scoreJ1 += scoreTmp
                            self.ajouterCouleurJ1(couleur)
                            caseSupprime = True
            else:
                if (joueur == 2 and self.nbJoueur == 2):
                    if (self.estMaCouleur(couleur, 2)):
                        scoreTmp = self.plateau.supprime(x, y)

                        if (scoreTmp != 0):
                            self.scoreJ2 += scoreTmp
                            self.ajouterCouleurJ2(couleur)
                            caseSupprime = True
            self.plateau.gravite() # On fait tomber les cases
            self.plateau.decalage() # On décale les cases
            if (not self.plateau.estJouable()):
                self.enJeu = False
            return caseSupprime

    def changementJoueur(self):
        """Méthode pour changer de joueur (de 1 à 2 et de 2 à 1)"""
        if (self.tourDeJeu == 1):
            self.tourDeJeu = 2
        else:
            self.tourDeJeu = 1

    def passerTour(self):
        """Méthode pour passer le tour à l'autre joueur si on est en mode 2 joueurs"""
        if (self.nbJoueur == 2 and self.enJeu):
            if (self.tourDeJeu == 1):
                if (self.plateau.estJouableTest(self.listeCouleurJ2 + self.listeCouleurRestante)):
                    self.changementJoueur()
                    return True
                else:
                    return False
            else:
                if (self.plateau.estJouableTest(self.listeCouleurJ1 + self.listeCouleurRestante)):
                    self.changementJoueur()
                    return True
                else:
                    return False
        else:
            return True

    def nouveauPlateau(self, x, y, nb):
        """Méthode pour réinitialiser un nouveau plateau de jeu"""
        self.enJeu = True
        self.nombrePartie += 1
        self.nbJoueur = nb
        self.tailleX = x
        self.tailleY = y
        self.plateau = Plateau.Plateau(x, y)
        self.plateau.aleatoire()
        self.scoreJ1 = 0
        self.scoreJ2 = 0
        self.tourDeJeu = 1
        self.listeCouleurJ1.clear()
        self.listeCouleurJ2.clear()
        self.listeCouleurRestante.clear()

        i = 1
        while (i <= self.plateau.nbCouleur):
            self.listeCouleurRestante.append(self.plateau.listeCouleur[i])
            i = i + 1

    def supprimerPlateau(self):
        """Méthode pour supprimer le plateau de jeu"""
        self.enJeu = False
        self.plateau = None
        self.scoreJ1 = 0
        self.listeCouleurJ1 = []
        self.scoreJ2 = 0
        self.listeCouleurJ2 = []
        self.listeCouleurRestante = []
        self.nbJoueur = 0
        self.joueurNumero = 0
        self.enJeu = False
        self.tailleX = 0
        self.tailleY = 0
        self.tourDeJeu = None

    def nouveauPlateauListe(self, taille, listeMap):
        """Méthode pour réinitialiser un nouveau plateau de jeu avec une liste de couleurs"""
        self.enJeu = True
        self.nombrePartie += 1
        self.nbJoueur = 2
        self.tailleX = taille
        self.tailleY = taille
        self.plateau = Plateau.Plateau(self.tailleX, self.tailleY)
        self.plateau.listePlateau(listeMap)
        self.scoreJ1 = 0
        self.scoreJ2 = 0
        self.tourDeJeu = 1
        self.listeCouleurJ1.clear()
        self.listeCouleurJ2.clear()
        self.listeCouleurRestante.clear()
        i = 1
        while (i <= self.plateau.nbCouleur):
            self.listeCouleurRestante.append(self.plateau.listeCouleur[i])
            i = i + 1

    def nbCase(self):
        """Méthode pour récupérer le nombre de cases du plateau (nb de cases 10x10 = 100 et 20x20 = 400)"""
        return self.tailleX * self.tailleY