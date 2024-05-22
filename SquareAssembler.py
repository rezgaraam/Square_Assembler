from Jeu import Modele, Fenetre
"""on importe les classes Modele et Fenetre du package Jeu
    on crée une instance de Modele et une instance de Fenetre
    puis on passe modele qu'on vient dde créer en argument à Fenetre de jeu 
"""
modele = Modele.Modele()
fenetre = Fenetre.Fenetre(modele)