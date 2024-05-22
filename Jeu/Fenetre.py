from tkinter import Tk, Menu, Canvas, Label, Toplevel, Button, Radiobutton, IntVar, StringVar, Entry, LabelFrame

import tkinter.font as tkFont
from tkinter.messagebox import showinfo
from Reseau import Reseau
import sys


class Fenetre:
    """Classe Fenetre qui gère l'affichage du jeu:
        - Affichage du plateau
        - Affichage du score
        -taile de la fenetre
        - Affichage du menu
    """
    def __init__(self, modele):
        # Initialisation du modèle
        self.modele = modele
        # Nom du joueur pour le mode réseau
        self.nom = ""
        # Taille de la fenetre
        self.tailleEcranX = 604
        self.tailleEcranY = 720
        self.root = Tk()
        #self.root.geometry("604x720") mais la fenetre n'est pas redimensionnable
        self.root.resizable(width=False, height=False)
        self.root.title("Square Assembler")
        self.root.geometry(str(self.tailleEcranX) + 'x' + str(self.tailleEcranY) + '+200+200')
        self.win = None
        self.winDuree = None

        # Menu
        menubar = Menu(self.root)
        # Menu Jeu et ses sous menu
        filemenu = Menu(menubar, tearoff=0)
        filemenu.add_command(label="Nouveau", command=self.fenetreChoix)
        filemenu.add_command(label="Nouveau en ligne", command=self.boutonConnexion)

        filemenu.add_separator()
        filemenu.add_command(label="Quitter", command=self.fermeture)
        menubar.add_cascade(label="Jeu", menu=filemenu)
        # Menu "A propos" et son sous menu
        editmenu = Menu(menubar, tearoff=0)
        editmenu.add_command(label="Numéro d'anonymat", command=self.aPropos)
        menubar.add_cascade(label="A propos", menu=editmenu)
        # affichage du menu
        self.root.config(menu=menubar)

        # Affichage de la map
        self.taillePlateauX = 600
        self.taillePlateauY = 600
        self.canvasPlateau = Canvas(self.root, width=self.taillePlateauX, height=self.taillePlateauY, borderwidth=0)
        self.canvasPlateau.bind('<Button-1>', self.cliqueGauche)
        self.canvasPlateau.grid(row=1, column=0, padx=0, columnspan=3)

        # Affichage du score
        self.tailleScoreX = 600
        self.tailleScoreY = 70
        self.canvasScore = Canvas(self.root, width=self.tailleScoreX, height=self.tailleScoreY, borderwidth=0, bg=None)
        self.canvasScore.grid(row=0, column=0, columnspan=3)

        # Bouton passer
        #police = tkFont.Font(family='Impact', size=12)
        policeBoutonPasser = tkFont.Font(family='Helvetica', size=12, weight="bold")
        self.boutonPasser = Button(self.root, state='disabled', text='>> PASSER SON TOUR >>',
                                   command=self.boutonChangementTour, disabledforeground='#b7b7b7', font=policeBoutonPasser)
        self.boutonPasser.grid(row=2, column=2)
        # Le temps
        policeTemps = tkFont.Font(family='Helvetica', size=20, weight="bold")
        self.label = Label(self.root, text="", font=policeTemps)
        self.label.grid(row=2, column=1)
        self.dureeTour = -1
        self.temps = -1
        self.messageRejouez = False
        # PARTIE RESEAU
        self.reseau = None
        self.iniIvy = False
        self.surLeReseau = False
        self.connexion = False
        self.maj()
        self.root.protocol("WM_DELETE_WINDOW", self.fermeture) # Pour gérer la fermeture de la fenêtre
        self.root.mainloop()

    def maj(self):
        self.canvasScore.delete("all")
        self.canvasPlateau.delete("all")
        # titre / score / joueur
        self.affichageTitre()
        # Affichage si le jeu est en cours
        if (self.modele.existePlateau()):
            self.affichagePlateau()
        # Affichage fin de jeu
        if (not self.modele.enJeu and self.modele.nbJoueur != 0):
            self.affichageFinDePartie()
        # Gestion bouton passer
        if (self.modele.nbJoueur != 0):
            if (self.modele.nbJoueur == 1 or not self.modele.enJeu):
                self.boutonPasser.config(state="disabled")
            else:
                self.boutonPasser.config(state="normal")

    def affichagePlateau(self):
        self.canvasPlateau.delete("all")
        tailleCarre = self.tailleScoreX / self.modele.tailleX
        # Affichage du plateau
        x = 0
        while x < self.modele.tailleX:
            y = 0
            while y < self.modele.tailleY:
                self.canvasPlateau.create_rectangle(x * tailleCarre, y * tailleCarre, x * tailleCarre + tailleCarre,
                                                    y * tailleCarre + tailleCarre,
                                                    fill=self.modele.plateau.getCouleur(x, y))
                y = y + 1
            x = x + 1

    def affichageFinDePartie(self):
        police = tkFont.Font(family='Impact', size=30)
        self.canvasPlateau.create_text(self.taillePlateauX / 2, self.taillePlateauY / 2 - 20, text="FIN DU JEU",
                                       font=police)
        if (self.modele.nbJoueur == 1):
            self.canvasPlateau.create_text(self.taillePlateauX / 2, self.taillePlateauY / 2 + 20,
                                           text="SCORE FINAL: " + str(self.modele.scoreJ1), font=police)
        if (self.modele.nbJoueur == 2):
            if (self.connexion):
                if (self.modele.scoreJ1 > self.modele.scoreJ2):
                    if (self.modele.joueurNumero == 1):
                        self.canvasPlateau.create_text(self.taillePlateauX / 2, self.taillePlateauY / 2 + 20,
                                                       text="VICTOIRE", font=police)
                    else:
                        self.canvasPlateau.create_text(self.taillePlateauX / 2, self.taillePlateauY / 2 + 20,
                                                       text="DEFAITE", font=police)
                else:
                    if (self.modele.scoreJ2 > self.modele.scoreJ1):
                        if (self.modele.joueurNumero == 2):
                            self.canvasPlateau.create_text(self.taillePlateauX / 2, self.taillePlateauY / 2 + 20,
                                                           text="VICTOIRE", font=police)
                        else:
                            self.canvasPlateau.create_text(self.taillePlateauX / 2, self.taillePlateauY / 2 + 20,
                                                           text="DEFAITE", font=police)
                    else:
                        self.canvasPlateau.create_text(self.taillePlateauX / 2, self.taillePlateauY / 2 + 20,
                                                       text="EGALITE", font=police)
            else:
                if (self.modele.scoreJ1 > self.modele.scoreJ2):
                    self.canvasPlateau.create_text(self.taillePlateauX / 2, self.taillePlateauY / 2 + 20,
                                                   text="VICTOIRE JOUEUR 1", font=police)
                else:
                    if (self.modele.scoreJ2 > self.modele.scoreJ1):
                        self.canvasPlateau.create_text(self.taillePlateauX / 2, self.taillePlateauY / 2 + 20,
                                                       text="VICTOIRE JOUEUR 2", font=police)
                    else:
                        self.canvasPlateau.create_text(self.taillePlateauX / 2, self.taillePlateauY / 2 + 20,
                                                       text="EGALITE", font=police)

    def changementTour(self):
        if (self.modele.enJeu):
            if (not self.modele.passerTour()):
                if (self.connexion):
                    if (self.modele.joueurNumero == self.modele.tourDeJeu):
                        police = tkFont.Font(family='Impact', size=30)
                        self.maj()
                        self.canvasPlateau.create_text(self.taillePlateauX / 2, self.taillePlateauY / 2 + 20,
                                                       text="REJOUEZ", font=police)
                        self.messageRejouez = True
                else:
                    police = tkFont.Font(family='Impact', size=30)
                    self.maj()
                    self.canvasPlateau.create_text(self.taillePlateauX / 2, self.taillePlateauY / 2 + 20,
                                                   text="REJOUEZ", font=police)
                    self.messageRejouez = True
            else:
                self.messageRejouez = False
                self.maj()
            self.temps = self.dureeTour

            self.majHorloge()  # pour afficher le nouveau temps
        else:
            if (self.modele.nbJoueur == 2):
                self.maj()

    def majHorloge(self):
        """Méthode pour mettre à jour l'horloge de la partie en cours si il reste 5 secondes ou moins on affiche en rouge sinon en noir"""
        if (self.modele.enJeu and self.modele.nbJoueur == 2):
            if (self.temps <= 5):
                self.label.configure(text=self.strEntier(self.temps, len(str(self.dureeTour))), fg="red")
            else:
                self.label.configure(text=self.strEntier(self.temps, len(str(self.dureeTour))), fg="black")
        else:
            self.label.configure(text="0", fg="grey")

    def lancer_horloge(self, duree):
        self.horlogePartie = self.modele.nombrePartie
        self.dureeTour = duree
        self.temps = duree
        self.tick_horloge(self.modele.nombrePartie)

    def tick_horloge(self, partie):
        self.temps -= 1
        if (self.temps <= 0):
            self.changementTour()
        else:
            self.majHorloge()
        if (self.modele.enJeu and self.modele.nbJoueur == 2 and partie == self.horlogePartie):
            self.root.after(1000, lambda: self.tick_horloge(partie))

    def strEntier(self, nombre, taille):
        """Méthode pour changer un entier en string avec un nombre de caractère donné"""
        tmp = str(nombre)
        while (len(tmp) < taille):
            tmp = "0" + tmp
        return tmp

    def strScore(self, joueur):
        tailleMax = 3
        if (joueur == 1):
            score = str(self.modele.scoreJ1)
        else:
            score = str(self.modele.scoreJ2)
        taille = len(score)
        while (tailleMax - taille > 0):
            score = "0" + score
            taille = len(score)
        if (self.modele.nbJoueur < joueur):
            score += "/000"
        else:
            score += "/" + str(self.modele.nbCase())

        return score

    def aPropos(self):
        showinfo("Numéro d'anonymat", "developpeur1= 23000053 \n\n developpeur2= 23000032")

    def fenetreChoix(self):
        tailleX = 365
        tailleY = 250
        numero = str(self.root.geometry()).split('+')
        posX = int(numero[1])
        posY = int(numero[2])
        positionX = int(posX + (self.tailleEcranX / 2) - (tailleX / 2))
        positionY = int(posY + (self.tailleEcranY / 2) - (tailleY / 2))
        geo = str(tailleX) + "x" + str(tailleY) + "+" + str(positionX) + "+" + str(positionY)

        self.win = Toplevel(self.root)
        self.win.geometry(geo)
        self.win.title("Changement de plateau")
        self.win.resizable(width=False, height=False)

        Label(self.win, text="Choisissez la taille du plateau:", width=41, height=2).grid(row=0, column=0, columnspan=2)
        varTaille = IntVar()
        varTaille.set(0)
        Radiobutton(self.win, width=10, height=3, variable=varTaille, text='10x10', value=10, indicatoron=0).grid(row=1,
                                                                                                                  column=0,
                                                                                                                  padx=0)
        Radiobutton(self.win, width=10, height=3, variable=varTaille, text='20x20', value=20, indicatoron=0).grid(row=1,
                                                                                                                  column=1,
                                                                                                                  padx=0)

        Label(self.win, text="Choisissez le nombre de joueur:", width=41, height=2).grid(row=2, column=0, columnspan=2)
        varJoueur = IntVar()
        varJoueur.set(0)
        Radiobutton(self.win, width=10, height=3, variable=varJoueur, text='1 joueur', value=1, indicatoron=0).grid(row=3, column=0)
        Radiobutton(self.win, width=10, height=3, variable=varJoueur, text='2 joueurs', value=2, indicatoron=0).grid(row=3, column=1)
        canvasLigne = Canvas(self.win, width=300, height=10)
        canvasLigne.create_line(10, 7, 290, 7)
        canvasLigne.grid(row=4, column=0, columnspan=2)
        Button(self.win, text='VALIDER', command=lambda: self.nouveau(varTaille.get(), varJoueur.get())).grid(row=5,column=0)
        Button(self.win, text='ANNULER', command=self.win.destroy).grid(row=5, column=1)

    def fenetreDuree(self, varTaille):
        """Méthode pour créer une fenêtre pour choisir la durée d'un tour"""
        tailleX = 320
        tailleY = 150
        numero = str(self.root.geometry()).split('+')
        posX = int(numero[1])
        posY = int(numero[2])
        positionX = int(posX + (self.tailleEcranX / 2) - (tailleX / 2))
        positionY = int(posY + (self.tailleEcranY / 2) - (tailleY / 2))
        geo = str(tailleX) + "x" + str(tailleY) + "+" + str(positionX) + "+" + str(positionY)
        self.winDuree = Toplevel(self.root)
        self.winDuree.geometry(geo)
        self.winDuree.title("Durée")
        self.winDuree.resizable(width=False, height=False)
        Label(self.winDuree, text="Choisissez la durée d'un tour:").grid(row=0, column=0, columnspan=2,sticky="nsew")
        value = IntVar()
        value.set(10)
        entree = Entry(self.winDuree, textvariable=value, width=30)
        entree.grid(row=1, column=0, columnspan=2, padx=7)
        Label(self.winDuree, text="").grid(row=2, column=0, columnspan=2)
        Button(self.winDuree, text='VALIDER', command=lambda: self.nouveau2Joueurs(varTaille, value)).grid(row=3,column=0,pady=5)
        Button(self.winDuree, text='ANNULER', command=self.winDuree.destroy).grid(row=3, column=1, pady=5)

    def nouveau2Joueurs(self, taille, duree):
        """Méthode pour créer un nouveau plateau de jeu avec 2 joueurs et une durée de tour"""
        try:
            if (duree.get() > 0):
                self.modele.nouveauPlateau(taille, taille, 2)
                self.lancer_horloge(duree.get())
                self.maj()
                self.winDuree.destroy()
        except:
            # Affichage d'une erreur si la durée n'est pas un entier
            Label(self.winDuree, text="Erreur: Il faut un entier !", fg="red").grid(row=2, column=0, columnspan=2)

    def nouveau(self, taille, joueur):
        if (taille != 0 and joueur != 0):
            if (self.surLeReseau):
                self.reseau.on_die()
                self.surLeReseau = False
                self.connexion = False
            if (joueur == 1):
                self.modele.nouveauPlateau(taille, taille, joueur)
                self.maj()
            else:
                self.fenetreDuree(taille)
            self.win.destroy()
            # PARTIE 1 joueur / 2 joueurs / Réseau

    def affichageTitre(self):
        """Méthode pour afficher le titre et le score du jeu"""
        self.canvasScore.delete("all")
        # Titre
        #police = tkFont.Font(family='Impact', size=15)
        police = tkFont.Font(family='Helvetica', size=15, weight="bold")
        self.canvasScore.create_text(self.tailleScoreX/2,15, text="SQUARE", font=police)
        self.canvasScore.create_text(self.tailleScoreX/2, 35, text="ASSEMBLER", font=police)
        if (self.connexion):
            if (self.modele.joueurNumero == 1):
                self.canvasScore.create_text(100, 15, text=self.reseau.nom, font=police, fill="black")
                self.canvasScore.create_text(self.tailleScoreX - 100, 15, text=self.reseau.nomAdversaire, font=police,fill="black")
            else:
                self.canvasScore.create_text(100, 15, text=self.reseau.nom, font=police, fill="black")
                self.canvasScore.create_text(self.tailleScoreX - 100, 15, text=self.reseau.nomAdversaire, font=police,fill="black")
            # Affichage du score
            if (self.modele.joueurNumero == 1):
                self.canvasScore.create_text(100, 35, text=self.strScore(1), font=police, fill="black")
                self.canvasScore.create_text(self.tailleScoreX - 100, 35, text=self.strScore(2), font=police,fill="black")
            else:
                self.canvasScore.create_text(100, 35, text=self.strScore(2), font=police, fill="black")
                self.canvasScore.create_text(self.tailleScoreX - 100, 35, text=self.strScore(1), font=police,fill="black")
        else:
            # Affichages des joueurs
            if (self.modele.nbJoueur >= 1):
                color = "red"
            else:
                color = "grey"
            self.canvasScore.create_text(100, 15, text="Joueur-1", font=police, fill=color)
            self.canvasScore.create_text(100, 35, text=self.strScore(1), font=police, fill=color)
            if (self.modele.nbJoueur >= 2):
                color = "green"
            else:
                color = "grey"
            self.canvasScore.create_text(self.tailleScoreX - 100, 15, text="Joueur-2", font=police, fill=color)
            self.canvasScore.create_text(self.tailleScoreX - 100, 35, text=self.strScore(2), font=police, fill=color)
        # Ligne de séparation
        # self.canvasScore.create_line(0, 50, self.tailleScoreX, 50, width=2)
        # Ligne de séparation
        self.canvasScore.create_line(0, 45, 50, 45, width=2)  # ----
        # Affichage du joueur courant
        if (self.connexion):
            if (self.modele.joueurNumero == self.modele.tourDeJeu):
                self.canvasScore.create_line(50, 5, 50, 50, width=2)  # |
                self.canvasScore.create_line(50, 50, 150, 50, width=2)  # ---
                self.canvasScore.create_line(50, 5, 150, 5, width=2)  # ---
                self.canvasScore.create_line(150, 50, 150, 5, width=2)  # |
            else:
                self.canvasScore.create_line(50, 45, 50, 50, width=2)  # |
                self.canvasScore.create_line(50, 50, 150, 50, width=2)  # ---
                self.canvasScore.create_line(150, 50, 150, 45, width=2)  # |
        else:
            if (self.modele.tourDeJeu == 1):
                self.canvasScore.create_line(50, 5, 50, 50, width=2)  # |
                self.canvasScore.create_line(50, 50, 150, 50, width=2)  # ---
                self.canvasScore.create_line(50, 5, 150, 5, width=2)  # ---
                self.canvasScore.create_line(150, 50, 150, 5, width=2)  # |
            else:
                self.canvasScore.create_line(50, 45, 50, 50, width=2)  # |
                self.canvasScore.create_line(50, 50, 150, 50, width=2)  # ---
                self.canvasScore.create_line(150, 50, 150, 45, width=2)  # |

        self.canvasScore.create_line(150, 45, (self.tailleScoreX / 2) - 60, 45, width=2)  # ---

        self.canvasScore.create_line((self.tailleScoreX / 2) - 60, 45, (self.tailleScoreX / 2) - 60, 50, width=2)  # |
        self.canvasScore.create_line((self.tailleScoreX / 2) - 60, 50, (self.tailleScoreX / 2) + 60, 50, width=2)  # ---
        self.canvasScore.create_line((self.tailleScoreX / 2) + 60, 50, (self.tailleScoreX / 2) + 60, 45, width=2)  # |

        self.canvasScore.create_line((self.tailleScoreX / 2) + 60, 45, self.tailleScoreX - 150, 45, width=2)  # ---

        # Affichage du joueur ennemi
        if (self.connexion):
            if (self.modele.joueurNumero != self.modele.tourDeJeu):
                self.canvasScore.create_line(self.tailleScoreX - 150, 5, self.tailleScoreX - 150, 50, width=2)  # |
                self.canvasScore.create_line(self.tailleScoreX - 150, 50, self.tailleScoreX - 50, 50, width=2)  # ---
                self.canvasScore.create_line(self.tailleScoreX - 150, 5, self.tailleScoreX - 50, 5, width=2)  # ---
                self.canvasScore.create_line(self.tailleScoreX - 50, 50, self.tailleScoreX - 50, 5, width=2)  # |
            else:
                self.canvasScore.create_line(self.tailleScoreX - 150, 45, self.tailleScoreX - 150, 50, width=2)  # |
                self.canvasScore.create_line(self.tailleScoreX - 150, 50, self.tailleScoreX - 50, 50, width=2)  # ---
                self.canvasScore.create_line(self.tailleScoreX - 50, 50, self.tailleScoreX - 50, 45, width=2)  # |
        else:
            if (self.modele.tourDeJeu == 2):
                self.canvasScore.create_line(self.tailleScoreX - 150, 5, self.tailleScoreX - 150, 50, width=2)  # |
                self.canvasScore.create_line(self.tailleScoreX - 150, 50, self.tailleScoreX - 50, 50, width=2)  # ---
                self.canvasScore.create_line(self.tailleScoreX - 150, 5, self.tailleScoreX - 50, 5, width=2)  # ---
                self.canvasScore.create_line(self.tailleScoreX - 50, 50, self.tailleScoreX - 50, 5, width=2)  # |
            else:
                self.canvasScore.create_line(self.tailleScoreX - 150, 45, self.tailleScoreX - 150, 50, width=2)  # |
                self.canvasScore.create_line(self.tailleScoreX - 150, 50, self.tailleScoreX - 50, 50, width=2)  # ---
                self.canvasScore.create_line(self.tailleScoreX - 50, 50, self.tailleScoreX - 50, 45, width=2)  # |

        self.canvasScore.create_line(self.tailleScoreX - 50, 45, self.tailleScoreX, 45, width=2)  # ---

        # Affichage des carrés de couleurs
        tailleCarre = 14
        y = 54

        if (self.connexion):
            if (self.modele.joueurNumero == 1):
                # Couleur du joueur 1
                x = 100 - (len(self.modele.listeCouleurJ1) * tailleCarre) / 2
                i = 0
                while (i < len(self.modele.listeCouleurJ1)):
                    self.canvasScore.create_rectangle(x + tailleCarre * i, y, x + tailleCarre + tailleCarre * i,
                                                      y + tailleCarre, fill=self.modele.listeCouleurJ1[i])
                    i = i + 1

                # Couleur du joueur 2
                x = (self.tailleScoreX - 100) - (len(self.modele.listeCouleurJ2 * tailleCarre)) / 2
                i = 0
                while (i < len(self.modele.listeCouleurJ2)):
                    self.canvasScore.create_rectangle(x + tailleCarre * i, y, x + tailleCarre + tailleCarre * i,
                                                      y + tailleCarre, fill=self.modele.listeCouleurJ2[i])
                    i = i + 1
            else:
                # Couleur du joueur 1
                x = (self.tailleScoreX - 100) - (len(self.modele.listeCouleurJ2 * tailleCarre)) / 2

                i = 0
                while (i < len(self.modele.listeCouleurJ1)):
                    self.canvasScore.create_rectangle(x + tailleCarre * i, y, x + tailleCarre + tailleCarre * i,
                                                      y + tailleCarre, fill=self.modele.listeCouleurJ1[i])
                    i = i + 1

                # Couleur du joueur 2
                x = 100 - (len(self.modele.listeCouleurJ1) * tailleCarre) / 2
                i = 0
                while (i < len(self.modele.listeCouleurJ2)):
                    self.canvasScore.create_rectangle(x + tailleCarre * i, y, x + tailleCarre + tailleCarre * i,
                                                      y + tailleCarre, fill=self.modele.listeCouleurJ2[i])
                    i = i + 1

            # Couleur restante
            x = (self.tailleScoreX / 2) - (len(self.modele.listeCouleurRestante) * tailleCarre) / 2
            i = 0
            while (i < len(self.modele.listeCouleurRestante)):
                self.canvasScore.create_rectangle(x + tailleCarre * i, y, x + tailleCarre + tailleCarre * i,
                                                  y + tailleCarre, fill=self.modele.listeCouleurRestante[i])
                i = i + 1
        else:
            # Couleur du joueur 1
            x = 100 - (len(self.modele.listeCouleurJ1) * tailleCarre) / 2
            i = 0
            while (i < len(self.modele.listeCouleurJ1)):
                self.canvasScore.create_rectangle(x + tailleCarre * i, y, x + tailleCarre + tailleCarre * i,
                                                  y + tailleCarre, fill=self.modele.listeCouleurJ1[i])
                i = i + 1

            x = (self.tailleScoreX - 100) - (len(self.modele.listeCouleurJ2 * tailleCarre)) / 2
            i = 0
            while (i < len(self.modele.listeCouleurJ2)):
                self.canvasScore.create_rectangle(x + tailleCarre * i, y, x + tailleCarre + tailleCarre * i,
                                                  y + tailleCarre, fill=self.modele.listeCouleurJ2[i])
                i = i + 1

            x = (self.tailleScoreX / 2) - (len(self.modele.listeCouleurRestante) * tailleCarre) / 2
            i = 0
            while (i < len(self.modele.listeCouleurRestante)):
                self.canvasScore.create_rectangle(x + tailleCarre * i, y, x + tailleCarre + tailleCarre * i,
                                                  y + tailleCarre, fill=self.modele.listeCouleurRestante[i])
                i = i + 1

    def boutonChangementTour(self):
        """ Méthode pour passer le tour à l'autre joueur"""
        if (self.connexion):
            if (self.modele.tourDeJeu == self.modele.joueurNumero):
                self.changementTour()
                self.reseau.envoyer("passer tour")
        else:
            self.changementTour()

        # self.temps = self.dureeTour

        # self.majHorloge() # pour afficher le nouveau temps
        # self.maj()

    def cliqueGauche(self, event):
        if (self.modele.enJeu and self.modele.existePlateau()):
            if (self.messageRejouez):
                self.messageRejouez = False
                self.maj()
            else:
                tailleCarre = 600 / self.modele.tailleX
                x = (int)(event.x / tailleCarre)
                y = (int)(event.y / tailleCarre)
                if (x >= 0 and x < self.modele.tailleX and y >= 0 and y < self.modele.tailleY):
                    if (self.connexion):
                        if (self.modele.tourDeJeu == self.modele.joueurNumero):
                            passerLeTour = self.modele.supprimerCase(x, y, self.modele.tourDeJeu)
                            if (passerLeTour):
                                self.reseau.envoyer("click: " + str(x) + " " + str(y) + " ")
                                self.changementTour()
                    else:
                        passerLeTour = self.modele.supprimerCase(x, y, self.modele.tourDeJeu)
                        # si deux joueur est coup valide
                        if (self.modele.nbJoueur == 2 and passerLeTour):
                            self.changementTour()
                        else:
                            self.maj()

                    # self.maj()

    # PARTIE 2 JOUEURS RESEAU
    def boutonConnexion(self):
        if (self.surLeReseau):
            if (self.connexion):
                if (self.reseau.estServeur):
                    self.fenetreChoixEnLigne()
                else:
                    self.reseau.envoyer("nouvelle partie")
        else:
            if (self.iniIvy):
                self.connexion2Joueur(self.reseau.nom)
            else:
                self.fenetreConnexion()

    def fenetreConnexion(self):
        """petite Fenetre de connexion"""
        tailleX = 295
        tailleY = 120
        numero = str(self.root.geometry()).split('+')
        posX = int(numero[1])
        posY = int(numero[2])
        positionX = int(posX + (self.tailleEcranX / 2) - (tailleX / 2))
        positionY = int(posY + (self.tailleEcranY / 2) - (tailleY / 2))
        geo = str(tailleX) + "x" + str(tailleY) + "+" + str(positionX) + "+" + str(positionY)
        self.windowConnexion = Toplevel(self.root) # creation de la fenetre de connexion sur la fenetre principale
        self.windowConnexion.geometry(geo)
        self.windowConnexion.title("Créer une partie en ligne 2 joueurs")
        self.windowConnexion.resizable(width=False, height=False)
        Label(self.windowConnexion, text="Choisissez votre pseudo :").grid(row=0, column=0, columnspan=2)
        value = StringVar()
        value.set("")
        entree = Entry(self.windowConnexion, textvariable=value, width=30)
        entree.grid(row=1, column=0, columnspan=2, padx=7)
        Label(self.windowConnexion, text="[9 caractères max. / sans espace]").grid(row=2, column=0, columnspan=2)
        Button(self.windowConnexion, text='CONNEXION', command=lambda: self.connexion2Joueur(value.get())).grid(row=3, column=0,pady=5)
        Button(self.windowConnexion, text='ANNULER', command=self.windowConnexion.destroy).grid(row=3, column=1, pady=5)

    def connexion2Joueur(self, nom):
        """méthode qui verifie si le nom est valide et si la connexion est possible"""
        if (not " " in nom and len(nom) <= 9 and nom != ""):
            if (not self.iniIvy):
                self.reseau = Reseau.Reseau(self, nom)
                self.reseau.initialisation()
                self.iniIvy = True
            self.reseau.connexion()
            self.surLeReseau = True
            self.modele.enJeu = False
            self.maj()
            police = tkFont.Font(family = 'Helvetica',weight = "bold", size=20)
            self.canvasPlateau.delete("all")
            self.canvasPlateau.create_text(300, 50, text="EN ATTENTE D'UN DEUXIEME JOUEUR", font=police)
            self.windowConnexion.destroy()

    def connexionReussi(self):
        """méthode qui permet de lancer la partie si la connexion est reussi"""
        if (self.reseau.estServeur):
            self.fenetreChoixEnLigne()
        self.maj()

    def deconnexion(self):
        """méthode qui affiche un message de deconnexion si le joueur est deconnecté"""
        self.connexion = False
        self.modele.supprimerPlateau()

        #police = tkFont.Font(family='Impact', size=20)
        police = tkFont.Font(family = 'Helvetica',weight = "bold", size=20)
        self.canvasPlateau.delete("all")
        self.canvasPlateau.create_text(300, 50, text="LE JOUEUR " + self.reseau.nomAdversaire + " EST DECONNECTE",font=police)
        self.canvasPlateau.create_text(300, 100, text="EN ATTENTE D'UN DEUXIEME JOUEUR", font=police)

    def fenetreChoixEnLigne(self):
        """la fenetre de choix taille de plateau et mode de joueur (1 ou 2)"""
        tailleX = 370
        tailleY = 220
        numero = str(self.root.geometry()).split('+')
        posX = int(numero[1])
        posY = int(numero[2])
        positionX = int(posX + (self.tailleEcranX / 2) - (tailleX / 2))
        positionY = int(posY + (self.tailleEcranY / 2) - (tailleY / 2))
        geo = str(tailleX) + "x" + str(tailleY) + "+" + str(positionX) + "+" + str(positionY)
        self.win = Toplevel(self.root)
        self.win.geometry(geo)
        self.win.title("Création")
        self.win.resizable(width=False, height=False)
        Label(self.win, text="Choisissez la taille du plateau:", width=41, height=2).grid(row=0, column=0, columnspan=2)
        varTaille = IntVar()
        varTaille.set(0)
        Radiobutton(self.win, width=10, height=3, variable=varTaille, text='10x10', value=10, indicatoron=0).grid(row=1,column=0,padx=0)
        Radiobutton(self.win, width=10, height=3, variable=varTaille, text='20x20', value=20, indicatoron=0).grid(row=1,column=1,padx=0)
        Label(self.win, text="Choisissez la durée d'un tour:").grid(row=2, column=0, columnspan=2)
        value = IntVar()
        value.set(10) # valeur par defaut de la durée d'un tour
        entree = Entry(self.win, textvariable=value, width=30)
        entree.grid(row=3, column=0, columnspan=2, padx=7)

        Label(self.win, text="").grid(row=4, column=0, columnspan=2)

        canvasLigne = Canvas(self.win, width=300, height=10)
        canvasLigne.create_line(10, 7, 290, 7)
        canvasLigne.grid(row=5, column=0, columnspan=2)

        Button(self.win, text='VALIDER', command=lambda: self.nouveau2JoueursEnLigne(varTaille, value)).grid(row=6,
                                                                                                             column=0)
        Button(self.win, text='ANNULER', command=self.win.destroy).grid(row=6, column=1)

    def demandeNouvellePartie(self):
        windowNouvellePartie = Toplevel(self.root)
        strtmp = "Le joueur " + self.reseau.nomAdversaire + " demande de faire une nouvelle partie. Acceptez-vous ?"
        lb = Label(windowNouvellePartie, text=strtmp)
        tailleX = lb.winfo_reqwidth()
        tailleY = 50
        numero = str(self.root.geometry()).split('+')
        posX = int(numero[1])
        posY = int(numero[2])
        positionX = int(posX + (self.tailleEcranX / 2) - (tailleX / 2))
        positionY = int(posY + (self.tailleEcranY / 2) - (tailleY / 2))
        geo = str(tailleX) + "x" + str(tailleY) + "+" + str(positionX) + "+" + str(positionY)
        windowNouvellePartie.geometry(geo)
        windowNouvellePartie.title("Demande")
        windowNouvellePartie.resizable(width=False, height=False)
        lb.grid(row=0, column=0, columnspan=2)
        Button(windowNouvellePartie, text='OUI', command=lambda: [self.fenetreChoixEnLigne(), windowNouvellePartie.destroy()]).grid(row=1, column=0)
        Button(windowNouvellePartie, text='NON', command=windowNouvellePartie.destroy).grid(row=1, column=1)

    def nouveau2JoueursEnLigne(self, taille, duree):
        """méthode qui permet de lancer une nouvelle partie en ligne avec un autre joueur"""
        try:
            # QUE POUR LA PARTIE SERVEUR
            if (duree.get() > 0 and (taille.get() == 10 or taille.get() == 20)):
                self.modele.nouveauPlateau(taille.get(), taille.get(), 2)
                # on envoie le modele
                self.reseau.envoyer("tour: " + str(duree.get()) + " ")
                self.reseau.envoyer("taille: " + str(taille.get()) + " ")
                self.reseau.envoyer("map: " + str(self.modele.plateau.getPlateauLineaire()) + " ")
                self.reseau.envoyer("Infos ok")
                self.connexion = True
                self.modele.joueurNumero = 1
                self.win.destroy()
                self.lancer_horloge(duree.get())
                self.maj()
        except:
            Label(self.win, text="Erreur: Il faut un entier !", fg="red").grid(row=4, column=0, columnspan=2)

    def chargementInformations(self):
        # QUE POUR LA PARTIE CLIENT
        self.connexion = True
        self.modele.joueurNumero = 2
        self.modele.nouveauPlateauListe(self.reseau.taille, self.reseau.map)
        self.lancer_horloge(self.reseau.dureeTour)
        self.maj()

    def cliqueReseau(self, x, y):
        if (self.modele.tourDeJeu != self.modele.joueurNumero):
            if (self.modele.enJeu and self.modele.existePlateau()):
                if (self.connexion):
                    self.modele.supprimerCase(x, y, self.modele.tourDeJeu)
                    self.changementTour()
                    self.maj()

    def fermeture(self):
        """méthode qui permet de fermer la fenetre de jeu en coupant la connexion"""
        if (self.surLeReseau):
            self.reseau.on_die()
        sys.exit()


