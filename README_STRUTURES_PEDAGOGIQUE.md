# Pricer de produits structurés — comprendre le code et savoir le défendre

Guide du fichier [strutu_engine_pedagogique.py](strutu_engine_pedagogique.py) : Phoenix standard, memory, bonus, step-up, sans autocall, custom strike, Zenith, Phoenix Double Memory et Phoenix Japan 2.

Ce README suit le même principe que ton guide du pricer d’options : **lire le vrai code, le traduire en français, comprendre pourquoi il est écrit ainsi et savoir ce qui change si l’on modifie un argument.** Les extraits et numéros de lignes correspondent au fichier pédagogique livré avec ce document. Le moteur n’est pas modifié par ce guide.

Les exemples de trajectoires servent à comprendre les paiements. Ce sont des scénarios choisis à la main, pas des prévisions de marché. Les noms commerciaux des produits ne suffisent pas à définir leur contrat : les règles décrites ici sont celles de ce fichier.

## Sommaire

- [1. Projet, installation et premier calcul](#projet)
- [2. Vocabulaire financier et unités](#vocabulaire)
- [3. Lire Python et NumPy sans être spécialiste](#syntaxe)
- [4. Les formules à comprendre](#formules)
- [5. Simulation, bloc par bloc](#simulation)
- [6. Phoenix, bloc par bloc](#phoenix)
- [7. Zenith, bloc par bloc](#zenith)
- [8. Double Memory, bloc par bloc](#dm)
- [9. Japan 2, bloc par bloc](#japan)
- [10. Choisir les arguments de chaque produit](#appels)
- [11. Limites, vérifications et questions d’oral](#oral)

<a id="projet"></a>
## 1. Projet, installation et premier calcul

### 1.1 À quoi sert ce fichier ?

Il simule plusieurs évolutions possibles du sous-jacent, applique les règles du produit dans chaque scénario, actualise les paiements et en calcule la moyenne.

**Circuit :** paramètres → trajectoires → coupons et remboursement → actualisation → prix moyen.

| Élément | Rôle |
|---|---|
| `strutu_engine_pedagogique.py` | Les cinq fonctions de simulation et de valorisation |
| NumPy | Les tableaux, les tirages aléatoires et les calculs numériques |
| `pricer_engine.py` | Un autre moteur ; il n’est pas importé ici |
| `exemple_structure.py` | Petit fichier que tu peux créer pour appeler le moteur |

Ce fichier ne lance ni serveur Flask ni interface. Exécuter seulement `python strutu_engine_pedagogique.py` définit les fonctions puis termine normalement, sans afficher de prix. Il faut **appeler une fonction**.

### 1.2 Première installation sur Mac

Place le fichier Python et ce README dans un même dossier. Dans Terminal, tape `cd ` avec un espace, glisse ce dossier dans la fenêtre, puis appuie sur Entrée. Exécute ensuite :

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install numpy
```

**Traduction en phrase :** Je crée un environnement Python pour ce dossier, je l’active, puis j’y installe NumPy. Si tu disposes déjà d’un environnement de projet contenant NumPy, tu peux utiliser cet environnement.

Les fois suivantes, depuis ce même dossier :

```bash
source .venv/bin/activate
python exemple_structure.py
```

### 1.3 Un premier exemple complet

Crée `exemple_structure.py` à côté du moteur et copie ce code :

```python
import numpy as np
from strutu_engine_pedagogique import price_phoenix

np.random.seed(42)

prix = price_phoenix(
    S0=100,
    r=0.03,
    q=0.01,
    sigma=0.20,
    obs_dates=[0.25, 0.50, 0.75, 1.00],
    K_auto=1.00,
    B_phoenix=0.80,
    B_pdi=0.60,
    coupon=0.02,
    n_simulations=10000,
    memory=True,
)

print("Prix pour un nominal de 1 :", prix)
print("Prix pour un nominal de 1 000 euros :", prix * 1000)
```

**Traduction en phrase :** J’importe les outils, je fixe les tirages pour pouvoir répéter mon calcul, puis je valorise un Phoenix avec quatre observations et un coupon de 2 % du nominal par période. J’affiche sa valeur pour deux tailles d’investissement.

Les valeurs numériques sont pédagogiques. Le coupon `0.02` n’est pas un coupon annuel automatiquement divisé par quatre. Le programme prend **2 % à chacune des quatre observations éligibles**. `memory=True` autorise le rattrapage des coupons manqués. `has_autocall` n’est pas renseigné : sa valeur par défaut est `True`.

<a id="vocabulaire"></a>
## 2. Vocabulaire financier et unités

| Mot ou argument | Sens dans ce moteur | Exemple |
|---|---|---|
| Sous-jacent, `S0` | Actif suivi et son prix initial | Une action vaut 100 |
| Nominal | Capital de référence du produit, fixé à 1 dans les calculs | 1 représente 100 % du capital |
| `r` | Taux annuel à composition continue | `0.03` = 3 % |
| `q` | Rendement continu de dividende | `0.01` = 1 % par an |
| `sigma` | Volatilité annuelle | `0.20` = 20 % |
| `obs_dates` | Dates depuis aujourd’hui, en années | `[0.5, 1.0]` = 6 mois puis 1 an |
| Fixing | Prix observé à une date | Le spot à 6 mois vaut 95 |
| `strike_pct` | Fraction de `S0` définissant le strike de référence | `0.90 × 100 = 90` |
| `K_auto` | Seuil de rappel, en fraction du strike | `1.00 × 90 = 90` |
| `B_phoenix` | Seuil de paiement du coupon | `0.80 × 90 = 72` |
| `B_pdi` | Seuil lié à la protection du capital | `0.60 × 90 = 54` |
| Coupon | Paiement conditionnel en fraction du nominal | `0.02` = 20 euros pour 1 000 euros |
| Autocall ou rappel | Remboursement automatique qui met fin au contrat | Le capital est rendu à 6 mois |
| Mémoire des coupons | Conservation des coupons manqués jusqu’à un fixing éligible | Deux coupons de 2 % donnent 4 % |
| Actualisation | Conversion d’un montant futur en valeur aujourd’hui | 1 dans un an vaut `exp(-r)` |
| Trajectoire | Un scénario complet de prix du sous-jacent | 100 → 85 → 105 |

**Trois nombres différents :** `S0=100` est le prix du sous-jacent ; le nominal interne vaut `1` ; le prix calculé du produit peut valoir par exemple `0.98`. Ce dernier nombre correspond à 980 euros pour 1 000 euros de nominal, pas à une probabilité de 98 %.

Dans Phoenix, Zenith et DM, la protection est testée sur le prix final des contrats non rappelés. Dans Japan 2, la barrière est surveillée sur toute la grille journalière, y compris aujourd’hui. Le mot « américaine » concerne ici cette surveillance de la barrière, pas un droit d’exercice libre de l’investisseur.

<a id="syntaxe"></a>
## 3. Lire Python et NumPy sans être spécialiste

### 3.1 Fonctions, arguments et indentation

`def` définit une fonction ; les parenthèses contiennent ses paramètres. `return` renvoie son résultat au programme appelant. Définir une fonction ne lance pas son calcul.

Dans `memory=True`, `True` est le défaut. Écrire `memory=False` lors de l’appel le remplace. `None` signifie ici « pas de valeur fournie » : `bonus_threshold=None` désactive le bonus, alors que `bonus_threshold=0` crée un seuil nul.

Les quatre espaces au début d’une ligne indiquent qu’elle appartient au bloc précédent. Déplacer `return` dans une boucle arrêterait le calcul au premier tour. `#` commence un commentaire ; le texte entre triples guillemets documente le module ou une fonction.

### 3.2 Le tableau `prix` : lignes et colonnes

```python
prix = np.array([
    [100,  90, 110],
    [100,  70,  60],
])
```

**Traduction en phrase :** Je construis deux trajectoires avec trois dates chacune, dont le prix initial.

| Écriture | Résultat | Pourquoi ? |
|---|---|---|
| `prix[0]` | `[100, 90, 110]` | Première ligne, indices à partir de 0 |
| `prix[:, 0]` | `[100, 100]` | Toutes les lignes, première colonne |
| `prix[:, 1]` | `[90, 70]` | Première observation après aujourd’hui |
| `prix[:, -1]` | `[110, 60]` | Dernière colonne |
| `prix[1, 2]` | `60` | Deuxième scénario, troisième date |
| `prix[:, 1:3]` | `[[90, 110], [70, 60]]` | Colonnes 1 et 2 ; la borne 3 est exclue |

`:` veut dire « tout » lorsqu’il est seul. La virgule sépare les axes. `prix[:, 0] = S0` remplit une colonne au lieu de la lire. `prix[:, 3]` serait hors du tableau ci-dessus.

### 3.3 `range`, `k-1` et `k+1`

| Expression | Valeurs parcourues |
|---|---|
| `range(3)` | 0, 1, 2 |
| `range(1, 4)` | 1, 2, 3 |
| `range(1, n_dates + 1)` avec 3 dates | 1, 2, 3 |

`obs_dates[0]` contient la première observation, mais `prix[:, 0]` contient aujourd’hui. D’où le couple `obs_dates[k-1]` et `prix[:, k]`. Le `+1` dans une tranche inclut la colonne courante puisque la borne de fin est exclue.

Changer `range(1, n_dates + 1)` en `range(1, n_dates)` oublierait la dernière observation et donc potentiellement le dernier coupon.

### 3.4 Nombres, listes et tableaux

`np.zeros(3)` crée `[0., 0., 0.]`. `np.zeros((2, 3))` crée deux lignes de trois cases. `np.zeros(3, dtype=bool)` crée trois `False`.

`np.full(3, 0.02)` crée trois coupons de 2 %. `np.asarray([0.01, 0.02, 0.03])` transforme une liste en tableau. `np.isscalar(0.02)` vaut `True`, mais `np.isscalar([0.02])` vaut `False` : une liste d’un élément n’est pas automatiquement répétée.

`liste.append(x)` ajoute x à une liste. `len(liste)` donne son nombre d’éléments. `periode.shape[1]` donne son nombre de colonnes ; `shape[0]` donnerait le nombre de scénarios.

### 3.5 Masques : une condition pour chaque scénario

```python
actifs = np.array([True, True, False])
S_k = np.array([90, 70, 110])
coupon_du = actifs & (S_k >= 80)
montant_coupon = np.where(coupon_du, 0.02, 0.0)
```

**Traduction en phrase :** Je paie 2 % seulement aux contrats encore actifs dont le prix observé atteint 80. Le troisième scénario ne reçoit rien, même avec un spot élevé, car le contrat est terminé.

`coupon_du` vaut `[True, False, False]` ; le paiement vaut `[0.02, 0, 0]`.

| Symbole | Sens |
|---|---|
| `=` | Affectation : enregistrer une valeur |
| `==` | Test d’égalité |
| `>=`, `<=` | Comparaison incluant l’égalité |
| `&` | ET entre deux tableaux de conditions |
| `\|` | OU entre deux tableaux de conditions |
| `~` | Inversion : True devient False |
| `+=` | Ajouter à la valeur existante |
| `**2` | Élever au carré |

`and` sert aux conditions simples telles que `has_autocall and k < n_dates`. Sur des tableaux de plusieurs booléens, utiliser `and` à la place de `&` provoque une erreur. Les parenthèses de `(S_k >= 80)` assurent que la comparaison est calculée avant le ET.

### 3.6 `np.where`, moyenne, maximum et axes

`np.where(condition, valeur_si_vrai, valeur_si_faux)` ne retire pas de scénarios : il choisit une valeur pour chaque position. Le remplacer par une sélection comme `S_k[condition]` change la longueur du tableau et fait perdre l’alignement avec les autres scénarios.

Pour `A = np.array([[80, 100], [90, 110]])` :

| Calcul | Résultat |
|---|---|
| `np.mean(A, axis=1)` | `[90, 100]` : moyenne temporelle de chaque scénario |
| `np.mean(A, axis=0)` | `[85, 105]` : moyenne entre scénarios à chaque date |
| `np.max(A, axis=1)` | `[100, 110]` : maximum de chaque scénario |
| `np.mean(A)` | `95` : moyenne de toutes les cases |

Pour des booléens, `.sum(axis=1)` compte les `True` de chaque ligne. `.any(axis=1)` demande s’il y en a au moins un. Ces deux calculs ne disent pas la même chose : « combien de jours ? » et « au moins une fois ? ».

`np.minimum([0.70, 1.20], 1.0)` donne `[0.70, 1.0]` : il plafonne chaque valeur à 1. `np.max` réduit un ensemble à son maximum ; `np.minimum` compare les valeurs élément par élément à un plafond.

<a id="formules"></a>
## 4. Les formules à comprendre

### 4.1 Simuler le sous-jacent

Sur une durée `dt`, le code utilise :

$$
S_{t+dt}=S_t\exp\left((r-q-\sigma^2/2)dt+\sigma\sqrt{dt}\,Z\right),\qquad Z\sim\mathcal N(0,1).
$$

- `r-q` est la croissance moyenne risque-neutre utilisée pour valoriser.
- `-sigma**2/2` corrige la croissance dans l’exponentielle.
- `sigma * sqrt(dt) * Z` produit le choc aléatoire.
- L’exponentielle conserve un prix positif pour un prix initial positif.

Avec `r=q=0`, `sigma=0.20`, `dt=0.25` et un choc choisi `Z=0`, l’exposant vaut `-0.005` : 100 devient environ 99.5012. Ce scénario isolé n’est pas la moyenne des trajectoires. Lorsque `sigma=0` et `r=q`, le prix reste constant.

### 4.2 Valoriser les paiements

$$
V_0\approx\frac{1}{N}\sum_{i=1}^{N}\sum_j F_{i,j}e^{-rt_j}.
$$

On additionne les paiements de chaque scénario, chacun actualisé à sa propre date ; puis on moyenne les scénarios. Un euro versé dans un an avec `r=0.03` vaut environ 0.97045 aujourd’hui. Un coupon versé à six mois est actualisé sur six mois, pas sur la maturité totale.

### 4.3 Remboursement final

Pour Phoenix, Zenith et DM, si le contrat n’a pas été rappelé :

$$
R_T=\begin{cases}1&\text{si }S_T\ge B_{pdi}\times strike_{reference},\\ S_T/strike_{reference}&\text{sinon.}\end{cases}
$$

Avec un strike de 100 et une barrière de 60 : prix final de 65 → capital de 1 ; prix final de 50 → capital de 0.50. Ce n’est pas la seule perte au-delà de 60 : la perte est mesurée par rapport au strike de 100.

Pour Japan 2, une barrière touchée pendant la vie du produit active `min(S_T / strike_reference, 1)`. Le capital reste plafonné à 1 même après un rebond. Les coupons s’ajoutent séparément au remboursement de capital.

<a id="simulation"></a>
## 5. Simulation, bloc par bloc

### 5.1 Import et fonction de simulation

**Lignes 22–27 de `strutu_engine_pedagogique.py`**

```python
import numpy as np


# Simulation aux dates d'observation

def simulate_observation_dates(S0, r, q, sigma, obs_dates, n_simulations):
```

**Traduction en phrase :** Je charge NumPy sous le nom court `np`, puis je définis la fonction qui construira les prix à chaque observation.

`S0`, `r`, `q`, `sigma`, les dates et le nombre de simulations sont fournis par l’appelant. Cette fonction simule le marché : elle ne connaît ni les coupons ni les barrières. Changer le nom de la fonction sans adapter ses appels casserait les fonctions de pricing.

**Lire les mots de cette ligne.** `import numpy` charge la bibliothèque ; `as np` donne un nom plus court pour l’utiliser. Ainsi `np.zeros` veut dire « utiliser la fonction zeros de NumPy ».

`def simulate_observation_dates(...)` crée une fonction. Les noms entre parenthèses reçoivent les valeurs transmises lors de l’appel. Elle renvoie un tableau de prix du sous-jacent, pas encore un prix de produit structuré.

Pour suivre toute cette section, prenons `S0=100`, `obs_dates=[0.25, 0.75]` et `n_simulations=2`. Nous avons deux scénarios et deux observations. Les chocs chiffrés plus loin sont choisis pour expliquer le calcul.


### 5.2 Préparer les trajectoires

**Lignes 33–38 de `strutu_engine_pedagogique.py`**

```python
    n_dates = len(obs_dates)
    prix = np.zeros((n_simulations, n_dates + 1))
    prix[:, 0] = S0

    # Tous les scénarios partent du même prix, à la date 0.
    t_precedent = 0
```

**Traduction en phrase :** Je compte les observations, prépare un tableau de prix, place le prix initial dans la première colonne et mémorise que nous partons de la date zéro.

Pour 2 scénarios et 4 observations, la forme est `(2, 5)`. Le `+1` réserve aujourd’hui. Sans lui, la dernière colonne manquerait. `np.zeros` prépare l’espace ; ses zéros ne sont pas des prix simulés définitifs.

**Regardons les tableaux se construire.**

`len(obs_dates)` compte deux éléments : `n_dates=2`. La ligne suivante demande donc `np.zeros((2, 3))` :

```text
prix au départ :
[[0, 0, 0],
 [0, 0, 0]]
```

Les doubles parenthèses ont un rôle : `(2, 3)` donne la forme du tableau, et les parenthèses extérieures appellent `np.zeros`. Deux lignes représentent les deux scénarios ; les trois colonnes représentent aujourd’hui et les deux observations.

`prix[:, 0] = S0` remplit ensuite toute la première colonne :

```text
[[100, 0, 0],
 [100, 0, 0]]
```

`:` sélectionne toutes les lignes, `0` sélectionne la première colonne. C’est une affectation : on écrit dans le tableau. Les autres zéros sont des cases à remplir au fil de la simulation.

`t_precedent = 0` garde la date depuis laquelle on va avancer. Cette variable contient un temps, pas le prix précédent.


### 5.3 Avancer de date en date

**Lignes 39–50 de `strutu_engine_pedagogique.py`**

```python
    for i in range(n_dates):
        t = obs_dates[i]
        dt = t - t_precedent
        # On tire un choc différent pour chaque scénario.
        Z = np.random.normal(0, 1, n_simulations)
        # On fait évoluer le prix entre les deux observations.
        croissance = (r - q - sigma**2 / 2) * dt
        choc = sigma * np.sqrt(dt) * Z
        prix[:, i+1] = prix[:, i] * np.exp(croissance + choc)
        t_precedent = t

    return prix
```

**Traduction en phrase :** Pour chaque date, je calcule le temps écoulé depuis la précédente, tire un choc par scénario, calcule les nouveaux prix et avance ma date de référence. Je renvoie ensuite le tableau entier.

Pour `[0.25, 0.75, 1.0]`, les durées sont `0.25`, `0.50`, `0.25`. Le code accepte donc des espacements irréguliers. Dans `normal(0, 1, n_simulations)`, 0 est la moyenne et 1 l’écart-type, pas la variance.

**Si on change le code :** retirer `t_precedent = t` ferait utiliser les durées depuis aujourd’hui à chaque étape, en les cumulant à tort. Remplacer `sqrt(dt)` par `dt` donnerait une mauvaise amplitude des chocs. Augmenter le nombre de scénarios réduit généralement le bruit mais consomme davantage de mémoire.

**Premier tour : `i=0`.** Ici, `i` numérote les observations, pas les scénarios. `range(2)` produit 0 puis 1.

1. `t = obs_dates[0]` donne `0.25`.
2. `dt = 0.25 - 0` donne une durée de `0.25` an.
3. `Z = np.random.normal(0, 1, 2)` tire deux nombres : un pour chaque scénario. Le 0 est la moyenne, le 1 l’écart-type, le 2 le nombre de valeurs demandées.

Prenons pour expliquer le calcul `r=q=0`, `sigma=0.20` et les chocs illustratifs `Z=[0, 1]` :

| Ligne | Calcul | Résultat |
|---|---|---|
| `croissance = (r - q - sigma**2 / 2) * dt` | `(0 - 0 - 0.04 / 2) * 0.25` | `-0.005` |
| `choc = sigma * np.sqrt(dt) * Z` | `0.20 * 0.5 * [0, 1]` | `[0, 0.10]` |
| `np.exp(croissance + choc)` | Exponentielle de `[-0.005, 0.095]` | Environ `[0.995012, 1.099659]` |

`**2` met au carré ; `np.sqrt` prend la racine carrée. Le nombre `croissance` est le terme de croissance du logarithme dans la formule, pas une prévision de rendement à annoncer à un investisseur.

Puis `prix[:, i+1] = prix[:, i] * ...` lit la colonne 0, multiplie chaque prix par son facteur, et écrit la colonne 1 :

```text
[[100,  99.5012, 0],
 [100, 109.9659, 0]]
```

`t_precedent = t` garde maintenant `0.25`.

**Deuxième tour : `i=1`.** `t` vaut `0.75` ; `dt` vaut `0.75 - 0.25 = 0.50`. On tire deux nouveaux chocs, lit la colonne 1 et remplit la colonne 2. Le prix précédent n’est donc plus 100 : c’est le prix simulé au tour précédent.

**Après la boucle**, `return prix` renvoie les deux lignes complètes. L’indentation est importante : placé dans la boucle, `return` arrêterait la fonction après la première observation.

La multiplication entre tableaux agit case par case. C’est pour cela qu’on peut simuler les deux scénarios sans écrire une boucle supplémentaire sur les lignes.


<a id="phoenix"></a>
## 6. Phoenix : suivre le code avec trois scénarios

Cette fonction simule les prix du sous-jacent, regarde les paiements dus dans chaque scénario et calcule leur valeur moyenne aujourd’hui. Nous allons suivre **les mêmes trois scénarios du début à la fin**, pour voir concrètement ce que contiennent les tableaux.

Les petits tableaux écrits dans les exemples servent à montrer les valeurs : dans le moteur, ce sont des tableaux NumPy.

### 6.1 Notre exemple pour toute la lecture

```python
S0 = 100
r = 0
q = 0
sigma = 0.20
obs_dates = [0.5, 1.0, 1.5]
K_auto = 1.00
B_phoenix = 0.80
B_pdi = 0.60
coupon = 0.02
n_simulations = 3
memory = True
has_autocall = True
bonus_threshold = None
bonus_amount = 0.0
strike_pct = 1.0
```

**Traduction en phrase :** Je considère un produit avec trois observations, un coupon de 2 % par période, une mémoire des coupons et un rappel possible avant maturité. Le taux est nul pour que les calculs à la main soient faciles.

Le taux nul est seulement un choix d’exemple : le code sait aussi actualiser avec un taux non nul. Trois simulations permettent de comprendre les tableaux ; ce n’est pas un nombre suffisant pour une estimation Monte-Carlo précise.

### 6.2 Définir la fonction : `def price_phoenix(...)`

```python
def price_phoenix(S0, r, q, sigma, obs_dates, K_auto, B_phoenix, B_pdi, coupon,
                   n_simulations, memory=True, has_autocall=True,
                   bonus_threshold=None, bonus_amount=0.0, strike_pct=1.0):
```

**Traduction en phrase :** Je crée une fonction appelée `price_phoenix`. Pour calculer un prix, elle reçoit les informations entre parenthèses.

`def` définit la fonction. Les paramètres sont les noms qu’elle utilisera pour les valeurs reçues. Le `:` annonce le bloc de code de la fonction ; les lignes décalées de quatre espaces lui appartiennent.

| Paramètre | Ce qu’il représente | Notre valeur |
|---|---|---|
| `S0` | Prix initial du sous-jacent | `100` |
| `r` | Taux annuel, utilisé notamment pour actualiser | `0` |
| `q` | Rendement annuel continu de dividende | `0` |
| `sigma` | Volatilité annuelle | `0.20` |
| `obs_dates` | Dates d’observation en années | `[0.5, 1.0, 1.5]` |
| `K_auto` | Barrière de rappel en fraction du strike | `1.00` |
| `B_phoenix` | Barrière coupon en fraction du strike | `0.80` |
| `B_pdi` | Barrière de protection à maturité | `0.60` |
| `coupon` | Coupon prévu par période | `0.02` |
| `n_simulations` | Nombre de trajectoires simulées | `3` |

Les paramètres écrits avec `=` ont une **valeur par défaut**. `memory=True` signifie : « si l’appelant ne précise rien, activer la mémoire ». Passer `memory=False` lors de l’appel remplace ce défaut.

| Option | Défaut | Conséquence |
|---|---|---|
| `memory` | `True` | Les coupons manqués peuvent être rattrapés |
| `has_autocall` | `True` | Le rappel anticipé est possible |
| `bonus_threshold` | `None` | Aucun seuil de bonus : bonus désactivé |
| `bonus_amount` | `0.0` | Montant du bonus nul |
| `strike_pct` | `1.0` | Le strike de référence vaut `S0` |

`None` signifie « aucune valeur fournie ». Ce n’est pas le nombre zéro : un seuil de bonus de zéro serait un seuil défini, alors que `None` désactive le bloc du bonus.

Le texte entre `"""` sous la signature documente la fonction. Il explique les options, mais ne réalise aucun calcul. Définir la fonction ne l’exécute pas : il faudra l’appeler.

### 6.3 Compter les observations : `len(obs_dates)`

```python
n_dates = len(obs_dates)
```

**Traduction en phrase :** Je compte combien de dates se trouvent dans la liste.

`len()` donne le nombre d’éléments. Avec `[0.5, 1.0, 1.5]`, `n_dates` vaut `3`. Ce nombre ne représente pas la durée : la durée est ici de 1.5 an.

Ajouter une quatrième date à la liste fera passer `n_dates` à 4 et ajoutera un tour de boucle.

### 6.4 Simuler les prix

```python
prix = simulate_observation_dates(S0, r, q, sigma, obs_dates, n_simulations)
```

**Traduction en phrase :** J’appelle la fonction de simulation et je garde son résultat dans la variable `prix`.

Pour notre explication, imaginons les trajectoires suivantes. **Ces valeurs sont choisies à la main pour suivre les paiements**, pas obtenues par les paramètres précédents et une graine particulière.

```python
prix = np.array([
    [100, 105, 95, 110],   # Scénario A
    [100,  70, 90,  85],   # Scénario B
    [100,  75, 70,  50],   # Scénario C
])
```

| Scénario | Colonne 0 : aujourd’hui | Colonne 1 : 0.5 an | Colonne 2 : 1 an | Colonne 3 : 1.5 an |
|---|---:|---:|---:|---:|
| A | 100 | 105 | 95 | 110 |
| B | 100 | 70 | 90 | 85 |
| C | 100 | 75 | 70 | 50 |

Une ligne est une trajectoire ; une colonne est une date. Trois observations nécessitent **quatre colonnes**, car le tableau contient aussi aujourd’hui.

Le programme a simulé toute la trajectoire, même si le produit est rappelé tôt. Ce sont ensuite les conditions de paiement qui empêchent d’utiliser les prix suivants pour verser de nouveaux montants à un contrat terminé.

### 6.5 Transformer les barrières en prix

```python
strike_reference = strike_pct * S0
K_auto_level = K_auto * strike_reference
B_phoenix_level = B_phoenix * strike_reference
B_pdi_level = B_pdi * strike_reference
```

**Traduction en phrase :** Je calcule le strike puis les prix exacts auxquels je vais comparer les fixings.

| Calcul | Résultat |
|---|---:|
| `1.0 * 100` | Strike de 100 |
| `1.00 * 100` | Rappel à 100 |
| `0.80 * 100` | Coupon à 80 |
| `0.60 * 100` | Protection à 60 |

Pourquoi ces multiplications ? Un prix simulé de 105 doit être comparé à 100, pas à la fraction `1.00`.

**Si tu changes `strike_pct` en `0.90`**, le strike devient 90 et les barrières 90, 72 et 54. Le point de départ de la simulation reste `S0=100`. Le strike intervient aussi dans la perte finale et dans le seuil absolu du bonus.

### 6.6 Préparer les coupons : nombre unique ou liste

```python
if np.isscalar(coupon):
    coupon_schedule = np.full(n_dates, coupon)
else:
    coupon_schedule = np.asarray(coupon)
```

**Traduction en phrase :** Si le coupon est une valeur unique, je la répète pour toutes les dates. Sinon, je transforme la liste fournie en tableau NumPy.

- `np.isscalar(coupon)` teste s’il s’agit d’une valeur unique. Ce n’est pas une validation financière du coupon.
- `np.full(n_dates, coupon)` crée `n_dates` cases contenant toutes `coupon`.
- `np.asarray(coupon)` conserve les valeurs de la liste sous forme de tableau.

Avec `coupon=0.02`, le calendrier contient `[0.02, 0.02, 0.02]`. Avec `coupon=[0.01, 0.02, 0.03]`, il contient ces trois montants différents : c’est un step-up si les coupons augmentent.

**Ce sont les coupons prévus, pas les coupons déjà payés.** La condition de paiement sera testée plus loin.

Une liste `[0.02]` n’est pas automatiquement répétée : il faut donner un nombre unique pour le répéter, ou une liste contenant un montant par date. Le code ne vérifie pas cette longueur ici.

### 6.7 Préparer les paiements enregistrés

```python
flux_actualises = np.zeros(n_simulations)
```

**Traduction en phrase :** Je crée une case par scénario pour enregistrer les paiements en valeur d’aujourd’hui. Au départ, toutes les sommes sont nulles.

`np.zeros(3)` donne un tableau de trois zéros :

```python
flux_actualises = [0.0, 0.0, 0.0]
#                  A    B    C
```

On y ajoutera les coupons et le capital au fur et à mesure. Ce n’est ni le tableau des prix du sous-jacent, ni le stock de coupons encore impayés.

### 6.8 Préparer le suivi des rappels

```python
rappele = np.zeros(n_simulations, dtype=bool)
```

**Traduction en phrase :** Je crée une case par scénario pour retenir si son contrat a déjà été rappelé. Au départ, la réponse est non pour tous.

`dtype` choisit le type des cases. `bool` signifie booléen : `True` ou `False`. Les zéros deviennent donc :

```python
rappele = [False, False, False]
```

| Valeur | Signification |
|---|---|
| `False` | Le contrat n’a pas encore été rappelé |
| `True` | Le contrat a déjà été rappelé et remboursé |

`dtype=bool` choisit le **type** du tableau. Pour changer la **valeur** du scénario A, on pourrait écrire `rappele[0] = True`. On n’écrit pas `dtype=True` pour enregistrer un rappel.

### 6.9 Préparer la mémoire des coupons

```python
coupons_en_attente = np.zeros(n_simulations)
```

**Traduction en phrase :** Je prépare une case par scénario pour les coupons qui restent à rattraper.

```python
coupons_en_attente = [0.0, 0.0, 0.0]
```

Au départ, aucun coupon n’a été manqué. Si B manque un coupon de 2 %, sa case pourra contenir `0.02`. Ce montant n’est pas encore payé : il ne doit donc pas être ajouté aux flux tant que la condition de paiement n’est pas satisfaite.

Les trois tableaux restent alignés : la première case parle toujours de A, la deuxième de B et la troisième de C.

### 6.10 Parcourir les dates : `for k in range(...)`

```python
for k in range(1, n_dates + 1):
```

**Traduction en phrase :** Pour chaque observation, exécute toutes les instructions décalées sous cette ligne.

Avec trois dates, cela revient à `range(1, 4)`. La borne de fin est exclue, donc `k` prend successivement les valeurs 1, 2 et 3.

| Tour de boucle | `k` | Observation |
|---|---:|---|
| Premier | 1 | 0.5 an |
| Deuxième | 2 | 1 an |
| Troisième | 3 | 1.5 an |

**`k` est le numéro d’une observation, pas le numéro d’un scénario.** NumPy traite tous les scénarios ensemble à chaque date. Une boucle `for i in range(n_simulations)` parcourrait au contraire les scénarios 0, 1 et 2 séparément.

Supprimer `+1` ferait oublier le dernier tour. L’indentation indique les lignes répétées ; celles revenues au niveau précédent seront exécutées après la boucle.

### 6.11 Récupérer la date : `obs_dates[k-1]`

```python
t_k = obs_dates[k-1]
```

**Traduction en phrase :** Je récupère la date correspondant au tour de boucle actuel.

| `k` | Expression | Valeur |
|---:|---|---:|
| 1 | `obs_dates[0]` | 0.5 |
| 2 | `obs_dates[1]` | 1.0 |
| 3 | `obs_dates[2]` | 1.5 |

Les indices commencent à zéro. Le `-1` fait correspondre le numéro d’observation, qui commence à 1, à la position de la liste, qui commence à 0. Sans lui, on commencerait à la deuxième date et on dépasserait la liste au dernier tour.

### 6.12 Récupérer les prix : `prix[:, k]`

```python
S_k = prix[:, k]
```

**Traduction en phrase :** Je prends toutes les lignes du tableau des prix, à la colonne de l’observation actuelle.

`:` signifie toutes les lignes. La virgule sépare la sélection des lignes de celle des colonnes.

```python
# À la première observation :
S_k = prix[:, 1]
# Valeurs : [105, 70, 75]

# À la deuxième observation :
S_k = prix[:, 2]
# Valeurs : [95, 90, 70]
```

Pourquoi `k` ici et `k-1` pour les dates ? Le tableau `prix` possède une colonne supplémentaire pour aujourd’hui, contrairement à `obs_dates`.

### 6.13 Actualiser à la date du paiement

```python
actualisation = np.exp(-r * t_k)
```

**Traduction en phrase :** Je calcule le coefficient permettant de ramener un paiement de cette date à sa valeur aujourd’hui.

`np.exp(x)` calcule l’exponentielle. Avec `r=0.05` et `t_k=1`, le coefficient vaut environ `0.9512`. Un capital de 1 versé dans un an vaut donc environ 0.9512 aujourd’hui dans ce modèle.

Dans notre exemple, `r=0`, donc `np.exp(0)=1`. Les paiements ne sont pas réduits.

Chaque paiement utilise sa propre date : prendre systématiquement la maturité pour actualiser les coupons intermédiaires changerait leur valeur.

### 6.14 Garder les contrats encore actifs : `~rappele`

```python
actifs = ~rappele
```

**Traduction en phrase :** Les contrats actifs sont ceux qui n’ont pas déjà été rappelés.

Sur un tableau NumPy booléen, `~` inverse chaque valeur : `True` devient `False`, et `False` devient `True`.

```python
# Au départ :
rappele = [False, False, False]
actifs  = [True,  True,  True]

# Après un rappel de A :
rappele = [True,  False, False]
actifs  = [False, True,  True]
```

Une écriture plus explicite donnant le même résultat sur ce tableau est `actifs = (rappele == False)`.

Ce n’est pas encore une condition sur le prix. On demande ici **qui est encore en vie avant de prendre les décisions de cette observation**. Un contrat rappelé à 105 reste terminé même si son prix simulé retombe ensuite à 95.

### 6.15 Vérifier si un rappel est autorisé

```python
if has_autocall and k < n_dates:
```

**Traduction en phrase :** Si le rappel est activé et si nous sommes avant la dernière observation, regarde quels contrats doivent être rappelés.

`and` impose les deux conditions. À la première observation, `True and 1 < 3` est vrai. À la dernière, `True and 3 < 3` est faux.

À maturité, le capital passera par le remboursement final. Cette distinction permet notamment de verser un éventuel bonus final aux contrats arrivés à maturité.

### 6.16 Décider des rappels du jour

```python
autocall_now = actifs & (S_k >= K_auto_level)
```

**Traduction en phrase :** Parmi les contrats actifs, rappelle ceux dont le prix atteint la barrière.

À la première observation :

```python
actifs = [True, True, True]
S_k = [105, 70, 75]
# Barrière : 100
# Comparaison des prix : [True, False, False]
# Nouveaux rappels :     [True, False, False]
```

`&` signifie ET, case par case. Les parenthèses font calculer la comparaison avant le ET. `>=` inclut l’égalité : un prix de 100 suffit pour une barrière de 100.

Pour voir la même décision en regardant un scénario après l’autre, on pourrait écrire :

```python
autocall_now = np.zeros(n_simulations, dtype=bool)
for i in range(n_simulations):
    if rappele[i] == False:
        if S_k[i] >= K_auto_level:
            autocall_now[i] = True
```

Cette version suppose qu’on se trouve déjà dans le bloc où le rappel est autorisé. `i` est le numéro de la case ; `S_k[i]` est le prix dans cette case. Le moteur utilise NumPy pour effectuer ces comparaisons ensemble.

### 6.17 Sinon, aucun rappel aujourd’hui

```python
else:
    autocall_now = np.zeros(n_simulations, dtype=bool)
```

**Traduction en phrase :** Si le rappel est désactivé ou si nous sommes à maturité, aucun scénario n’est rappelé par ce bloc.

On obtient `[False, False, False]`. Cela ne remet pas les anciens rappels à zéro : `autocall_now` concerne seulement aujourd’hui, tandis que `rappele` conserve l’historique.

### 6.18 Décider qui a droit au coupon

```python
coupon_du = actifs & (S_k >= B_phoenix_level)
```

**Traduction en phrase :** Le coupon est dû si le contrat est actif et si le prix atteint sa barrière coupon.

Au premier tour, les prix sont `[105, 70, 75]` et la barrière vaut 80. Donc `coupon_du` contient `[True, False, False]`.

Le rappel et le coupon sont deux décisions distinctes. A remplit les deux conditions dans notre exemple. Avec d’autres niveaux de barrière, un rappel ne garantirait pas automatiquement le coupon.

### 6.19 Lire le coupon prévu pour cette période

```python
coupon_periode = coupon_schedule[k-1]
```

**Traduction en phrase :** Je prends le montant de coupon prévu pour l’observation actuelle.

Avec un coupon fixe, on lit 0.02 à chaque tour. Avec `[0.01, 0.02, 0.03]`, on lirait 0.01 au premier tour, puis 0.02, puis 0.03. Le `-1` vient à nouveau des indices qui commencent à zéro.

### 6.20 Avec mémoire, ajouter le coupon courant

```python
if memory:
    coupons_en_attente += np.where(actifs, coupon_periode, 0.0)
```

**Traduction en phrase :** Si la mémoire est activée, ajoute le coupon de cette période au stock de chaque contrat encore actif.

`np.where(condition, oui, non)` choisit une valeur par scénario. Ici, on ajoute le coupon si le scénario est actif, sinon zéro. `+=` signifie « ajoute à ce qui existe déjà ».

Au premier tour :

```python
# Stock avant :       [0.00, 0.00, 0.00]
# Coupons ajoutés :   [0.02, 0.02, 0.02]
# Stock après ajout : [0.02, 0.02, 0.02]
```

On ajoute d’abord le coupon du jour pour qu’il soit inclus si un paiement est possible maintenant. Remplacer `+=` par `=` écraserait les anciens coupons manqués et supprimerait leur mémoire.

### 6.21 Déterminer ce qui sera vraiment versé

```python
montant_coupon = np.where(coupon_du, coupons_en_attente, 0.0)
```

**Traduction en phrase :** Si le coupon est dû, verse tout le stock en attente du scénario ; sinon, verse zéro.

Au premier tour :

```python
# Coupon dû ?       [True, False, False]
# Stock disponible : [0.02, 0.02, 0.02]
# Paiement décidé :  [0.02, 0.00, 0.00]
```

A reçoit 2 %. B et C ne reçoivent rien pour le moment. Un montant prévu, un stock en attente et un paiement décidé sont trois informations différentes.

### 6.22 Vider le stock payé

```python
coupons_en_attente = np.where(coupon_du, 0.0, coupons_en_attente)
```

**Traduction en phrase :** Si les coupons viennent d’être payés, remets le stock à zéro. Sinon, conserve-le.

Après le premier tour, le stock vaut `[0.00, 0.02, 0.02]`. A n’a plus rien en attente ; B et C conservent leur coupon manqué.

L’ordre compte : on détermine d’abord le paiement, puis on vide le stock. Le vider avant ferait perdre le montant à payer ; ne jamais le vider ferait repayer les anciens coupons.

### 6.23 Sans mémoire, payer seulement le coupon courant

```python
else:
    montant_coupon = np.where(coupon_du, coupon_periode, 0.0)
```

**Traduction en phrase :** Si la mémoire est désactivée, paie seulement le coupon de la période lorsque la condition est satisfaite.

Un coupon de 2 % manqué puis un coupon de 2 % éligible donnent 4 % au second paiement avec mémoire, mais seulement 2 % sans mémoire. Cette branche n’est pas exécutée dans notre exemple puisque `memory=True`.

### 6.24 Enregistrer le coupon payé

```python
flux_actualises += montant_coupon * actualisation
```

**Traduction en phrase :** Ajoute le coupon effectivement payé, ramené en valeur d’aujourd’hui, aux paiements déjà enregistrés.

Au premier tour et avec notre taux nul :

```python
# Avant : [0.00, 0.00, 0.00]
# Ajout : [0.02, 0.00, 0.00]
# Après : [0.02, 0.00, 0.00]
```

On ajoute le paiement, pas tous les coupons en attente. Avec un taux non nul, chaque montant serait multiplié par le facteur d’actualisation de sa date.

### 6.25 Ajouter le capital en cas de rappel

```python
flux_actualises += np.where(autocall_now, 1.0 * actualisation, 0.0)
```

**Traduction en phrase :** Pour les contrats rappelés aujourd’hui, ajoute aussi le capital remboursé, actualisé à aujourd’hui.

`1.0` représente 100 % du nominal, pas le prix du sous-jacent. A est rappelé, donc on ajoute `[1.0, 0.0, 0.0]` dans notre exemple à taux nul.

Le tableau devient `[1.02, 0.00, 0.00]` : A a reçu son capital et son coupon.

### 6.26 Conserver l’historique des rappels

```python
rappele = rappele | autocall_now
```

**Traduction en phrase :** Un contrat est désormais rappelé s’il l’était déjà ou s’il vient de l’être aujourd’hui.

`|` signifie OU, case par case.

```python
# Rappels précédents : [False, False, False]
# Rappels du jour :    [True,  False, False]
# Historique obtenu : [True,  False, False]
```

Écrire seulement `rappele = autocall_now` pourrait faire oublier un rappel ancien à une date où il n’y en a pas de nouveau. Le contrat risquerait alors d’être considéré actif à tort.

### 6.27 Regarder ce qui se passe aux tours suivants

La boucle passe à `k=2`, puis à `k=3`. Voici l’évolution de nos trois scénarios :

| Observation | A | B | C |
|---|---|---|---|
| 1 : prix 105 / 70 / 75 | Coupon 2 % et capital ; terminé | 2 % en attente | 2 % en attente |
| 2 : prix 95 / 90 / 70 | Aucun paiement supplémentaire | Paiement de 4 %, mémoire vidée | 4 % en attente |
| 3 : prix 110 / 85 / 50 | Aucun paiement supplémentaire | Paiement de 2 % | 6 % en attente |

Après les trois observations, mais avant le capital final des survivants :

```python
flux_actualises = [1.02, 0.06, 0.00]
rappele = [True, False, False]
coupons_en_attente = [0.00, 0.00, 0.06]
```

C conserve 6 % en attente, mais aucune date n’a permis leur paiement. **La mémoire n’est pas une garantie de versement final.** Dans ce code, ces coupons restent impayés.

### 6.28 Après la boucle : les prix finaux

```python
S_T = prix[:, n_dates]
actualisation_T = np.exp(-r * obs_dates[-1])
non_rappelees = ~rappele
```

**Traduction en phrase :** Je récupère les prix à maturité, le facteur d’actualisation final et les contrats encore à rembourser.

Ces lignes ne sont plus dans la boucle : elles sont exécutées une seule fois, après toutes les observations.

- `prix[:, 3]` donne `[110, 85, 50]`.
- `obs_dates[-1]` prend le dernier élément, soit `1.5`. Ici `-1` veut dire « dernier », pas « première date moins un an ».
- Avec `r=0`, le facteur vaut 1.
- `non_rappelees` vaut `[False, True, True]`.

Seuls B et C attendent encore leur capital.

### 6.29 Calculer le capital final

```python
remboursement_T = np.where(S_T >= B_pdi_level, 1.0, S_T / strike_reference)
```

**Traduction en phrase :** Si le prix final atteint la barrière de protection, rembourse tout le capital. Sinon, rembourse le prix final divisé par le strike.

Avec un strike de 100 et une PDI de 60 :

| Scénario | Prix final | Calcul | Montant calculé |
|---|---:|---|---:|
| A | 110 | Prix supérieur à 60 | 1.00 |
| B | 85 | Prix supérieur à 60 | 1.00 |
| C | 50 | `50 / 100` | 0.50 |

Le tableau contient `[1.00, 1.00, 0.50]`. **Cette ligne calcule les montants mais ne les verse pas encore.** A sera filtré au moment d’ajouter les paiements, car son capital a déjà été rendu.

L’égalité à 60 protège le capital grâce à `>=`. Sous la barrière, la perte est calculée par rapport au strike : on ne rembourse pas `50 / 60` et on ne perd pas seulement la baisse au-delà de la barrière.

### 6.30 Vérifier s’il existe un bonus

```python
if bonus_threshold is not None:
```

**Traduction en phrase :** Si un seuil de bonus a été fourni, exécute le bloc de calcul du bonus.

Dans notre exemple initial, `bonus_threshold=None`, donc ce bloc est ignoré.

Pour illustrer le bloc, prenons temporairement `bonus_threshold=0.80` et `bonus_amount=0.05`. Cela définit un bonus de 5 % du nominal pour les contrats non rappelés dont le prix final atteint 80.

### 6.31 Décider qui reçoit le bonus

```python
bonus_du = non_rappelees & (S_T >= bonus_threshold * strike_reference)
remboursement_T = remboursement_T + np.where(bonus_du, bonus_amount, 0.0)
```

**Traduction en phrase :** Ajoute le bonus aux contrats non rappelés qui atteignent son seuil à maturité.

Avec les valeurs temporaires ci-dessus :

```python
# Bonus dû :                [False, True, False]
# Remboursement avec bonus : [1.00, 1.05, 0.50]
```

A ne reçoit pas de bonus parce qu’il a été rappelé, même si son prix final simulé est élevé. B le reçoit. C n’atteint pas le seuil.

Le bonus s’ajoute au remboursement ; le coupon final a déjà été traité dans la boucle. Le code teste le seuil du bonus indépendamment de la PDI : le choix des niveaux doit correspondre au contrat voulu.

Pour la suite, revenons à notre exemple **sans bonus**.

### 6.32 Verser le capital uniquement aux survivants

```python
flux_actualises += np.where(non_rappelees, remboursement_T * actualisation_T, 0.0)
```

**Traduction en phrase :** Ajoute le remboursement final actualisé seulement aux scénarios qui n’ont pas déjà été rappelés.

```python
# Total avant : [1.02, 0.06, 0.00]
# Ajout :       [0.00, 1.00, 0.50]
# Total après : [1.02, 1.06, 0.50]
```

Le filtre `non_rappelees` empêche de rembourser A deux fois. Le coupon final de B n’est pas ajouté à nouveau : il est déjà dans les 0.06.

### 6.33 Renvoyer le prix moyen

```python
return np.mean(flux_actualises)
```

**Traduction en phrase :** Fais la moyenne des paiements actualisés de tous les scénarios et renvoie ce nombre au programme appelant.

Avec nos trois trajectoires choisies à la main :

```python
# (1.02 + 1.06 + 0.50) / 3 = 0.86
```

Le résultat vaut **0.86 pour un nominal de 1**, soit **860 euros pour 1 000 euros de nominal**. Avec le bonus illustratif précédent, le total de B serait 1.11 au lieu de 1.06 et la moyenne changerait.

`return` renvoie une valeur ; il ne l’affiche pas automatiquement. Pour l’afficher, le programme appelant peut enregistrer le résultat puis utiliser `print(prix_produit)`.

Remplacer `np.mean` par `np.sum` additionnerait tous les scénarios sans diviser par leur nombre. Augmenter le nombre de simulations augmenterait alors artificiellement le résultat.

Le 0.86 de notre exemple n’est pas un prix de marché ni le résultat attendu d’un appel aléatoire avec les paramètres de départ. Il montre **comment trois sommes de paiements deviennent un seul prix**. Dans un vrai appel du moteur, la même logique s’applique à beaucoup plus de trajectoires simulées.


<a id="zenith"></a>
## 7. Zenith, bloc par bloc

### 7.1 Définir et préparer les paliers

**Lignes 146–166 de `strutu_engine_pedagogique.py`**

```python
def price_zenith(S0, r, q, sigma, obs_dates, K_levels, C_levels, B_pdi,
                  n_simulations, strike_pct=1.0):
    """Calcule le prix d'un Zenith à plusieurs paliers.

    Donner les barrières et leurs coupons dans l'ordre croissant,
    avec autant de coupons que de barrières.
    On paie le coupon du plus haut palier atteint. Seul le dernier
    palier déclenche aussi le remboursement du capital.
    """
    assert len(K_levels) == len(C_levels), "K_levels et C_levels doivent avoir la même longueur"

    n_dates = len(obs_dates)
    prix = simulate_observation_dates(S0, r, q, sigma, obs_dates, n_simulations)

    # Par exemple, une barrière de 80 % avec un strike de 100 donne 80.
    strike_reference = strike_pct * S0
    K_levels_abs = []
    for niveau in K_levels:
        K_levels_abs.append(niveau * strike_reference)
    B_pdi_level = B_pdi * strike_reference
    n_paliers = len(K_levels_abs)
```

**Traduction en phrase :** Je reçois une liste de seuils et une liste de coupons associés, vérifie leur longueur, simule les prix et convertis les seuils en niveaux absolus.

`assert` arrête normalement le calcul si les longueurs diffèrent, mais ne vérifie ni l’ordre ni que les listes sont non vides. Les assertions peuvent aussi être désactivées en mode Python optimisé. Fournir des seuils strictement croissants reste indispensable.

Pour un strike de 100, `[0.8, 1.0, 1.1]` devient `[80, 100, 110]`. La boucle et `.append` rendent cette conversion visible. `C_levels[i]` désigne le coupon associé au seuil de même position.

**Notre exemple suivi pour Zenith.** Prenons un strike de 100, un taux nul, une PDI à 60, deux observations à 0.5 et 1 an et trois scénarios. Les paliers sont :

| Position `i` | `K_levels[i]` | Seuil en prix | `C_levels[i]` |
|---:|---:|---:|---:|
| 0 | 0.80 | 80 | 0.01 |
| 1 | 1.00 | 100 | 0.02 |
| 2 | 1.10 | 110 | 0.04 |

`K_levels` contient des seuils ; `C_levels` contient les coupons associés. Leurs positions doivent se correspondre.

**Décortiquons la préparation.**

- `assert len(K_levels) == len(C_levels), "..."` demande que le nombre de seuils soit égal au nombre de coupons. `==` compare ; il n’affecte aucune valeur. Le texte après la virgule est le message affiché si l’assertion échoue.
- `n_dates = len(obs_dates)` donne ici 2.
- `prix = simulate_observation_dates(...)` crée une ligne de prix par scénario.
- `strike_reference = strike_pct * S0` donne 100 avec `strike_pct=1`.
- `K_levels_abs = []` crée une liste vide, à remplir.

La boucle `for niveau in K_levels` prend directement les valeurs 0.80, 1.00 puis 1.10. `niveau` n’est pas un indice. `.append(niveau * strike_reference)` ajoute successivement 80, 100 et 110 à la liste :

```text
[] → [80] → [80, 100] → [80, 100, 110]
```

`B_pdi_level` vaut `0.60 * 100 = 60`. `n_paliers = len(K_levels_abs)` vaut 3.

Pour suivre les paiements, nous choisissons ces trajectoires illustratives :

```text
           Aujourd’hui   Date 1   Date 2
A              100         115       90
B              100         105       95
C              100          70       50
```

Ces trajectoires servent à comprendre le code ; ce ne sont pas des résultats aléatoires garantis pour un jeu de paramètres.


### 7.2 Préparer la date et le coupon

**Lignes 169–180 de `strutu_engine_pedagogique.py`**

```python
    flux_actualises = np.zeros(n_simulations)
    # False au départ : aucun scénario n’a encore été rappelé.
    rappele = np.zeros(n_simulations, dtype=bool)

    for k in range(1, n_dates + 1):
        t_k = obs_dates[k-1]
        S_k = prix[:, k]
        actualisation = np.exp(-r * t_k)
        # On continue seulement les scénarios qui n’ont pas déjà été remboursés.
        actifs = ~rappele

        montant_coupon = np.zeros(n_simulations)
```

**Traduction en phrase :** Je prépare le suivi des contrats puis, à chaque date, je pars d’un coupon nul et je regarde les scénarios encore actifs.

Le coupon est remis à zéro **dans** la boucle des dates. Sinon, un coupon d’une ancienne observation pourrait rester présent alors qu’aucun palier n’est franchi aujourd’hui. Zenith n’utilise pas de stock de coupons impayés.

**Les tableaux au départ.** `np.zeros(3)` prépare `[0, 0, 0]` pour les paiements. Avec `dtype=bool`, les zéros de `rappele` deviennent `[False, False, False]` : aucun contrat n’est terminé.

`for k in range(1, n_dates + 1)` parcourt 1 puis 2. Au premier tour :

| Variable | Valeur | Ce qu’on vient de lire |
|---|---|---|
| `t_k` | 0.5 | `obs_dates[0]` |
| `S_k` | `[115, 105, 70]` | Toute la colonne 1 de `prix` |
| `actualisation` | 1 | `exp(-0 * 0.5)` |
| `actifs` | `[True, True, True]` | Inverse du tableau `rappele` |
| `montant_coupon` | `[0, 0, 0]` | Nouveau tableau pour cette date |

Le `~` inverse chaque booléen : il ne compare aucun prix à ce stade. On identifie d’abord les contrats encore vivants.

Le tableau de coupon est créé à nouveau à chaque observation. C’est nécessaire car la situation du jour détermine son montant, sans mémoire des coupons manqués dans ce Zenith.


### 7.3 Garder le coupon du meilleur palier

**Lignes 183–193 de `strutu_engine_pedagogique.py`**

```python
        for i in range(n_paliers):
            franchi = actifs & (S_k >= K_levels_abs[i])
            montant_coupon = np.where(franchi, C_levels[i], montant_coupon)

        # Le dernier palier rembourse aussi le capital.
        # Ici, on le teste même à la dernière observation.
        autocall_now = actifs & (S_k >= K_levels_abs[-1])
        flux_actualises += montant_coupon * actualisation
        flux_actualises += np.where(autocall_now, 1.0 * actualisation, 0.0)

        rappele = rappele | autocall_now
```

**Traduction en phrase :** Je parcours les paliers croissants. Chaque palier franchi remplace le coupon précédent. Le dernier palier déclenche également le remboursement du capital.

Avec des seuils 80, 100, 110 et des coupons 1 %, 2 %, 4 % : spot 95 → 1 % sans rappel ; spot 105 → 2 % sans rappel ; spot 115 → 4 % plus le capital. On ne verse pas `1 % + 2 % + 4 %`.

`K_levels_abs[-1]` est le dernier seuil. Ce n’est le plus élevé que si la liste est ordonnée. Remplacer l’affectation du coupon par une addition transformerait le produit en coupons cumulés. Dans ce fichier, le test de rappel existe aussi à la dernière observation.

**La boucle à l’intérieur de la boucle.** `k` choisit une date ; `i` choisit un palier à cette date. `range(n_paliers)` parcourt ici 0, 1 et 2.

`franchi = actifs & (S_k >= K_levels_abs[i])` teste, scénario par scénario : « encore actif ET prix supérieur ou égal au seuil de ce palier ? »

Puis `np.where(franchi, C_levels[i], montant_coupon)` veut dire : « si oui, prends le coupon de ce palier ; sinon, garde le montant déjà retenu ». Le troisième argument n’est pas zéro : on conserve le coupon d’un palier inférieur si le prix ne franchit pas le suivant.

Au premier fixing `[115, 105, 70]` :

| Tour `i` | Seuil testé | `franchi` | `montant_coupon` après le tour |
|---:|---:|---|---|
| 0 | 80 | `[True, True, False]` | `[0.01, 0.01, 0]` |
| 1 | 100 | `[True, True, False]` | `[0.02, 0.02, 0]` |
| 2 | 110 | `[True, False, False]` | `[0.04, 0.02, 0]` |

Le scénario A ne reçoit que 0.04, pas 0.07. Pour B, le dernier tour laisse 0.02 en place.

`K_levels_abs[-1]` prend le dernier seuil, 110. Le rappel vaut donc `[True, False, False]`.

Les deux lignes `flux_actualises += ...` enregistrent d’abord les coupons, puis le capital de 1 pour les rappels. Avec notre taux nul, le total devient `[1.04, 0.02, 0]`.

Enfin, `rappele = rappele | autocall_now` garde tous les rappels anciens ou nouveaux. Le symbole `|` est un OU case par case : A restera terminé même si son prix baisse ensuite.


### 7.4 Remboursement final du Zenith

**Lignes 195–205 de `strutu_engine_pedagogique.py`**

```python
    S_T = prix[:, n_dates]
    actualisation_T = np.exp(-r * obs_dates[-1])
    non_rappelees = ~rappele

    # À la barrière ou au-dessus, on rend tout le capital.
    # En dessous, on rembourse S_T / strike : par exemple 50 / 100 = 50 %.
    remboursement_T = np.where(S_T >= B_pdi_level, 1.0, S_T / strike_reference)
    flux_actualises += np.where(non_rappelees, remboursement_T * actualisation_T, 0.0)

    # On fait la moyenne de ce qui a été payé dans tous les scénarios.
    return np.mean(flux_actualises)
```

**Traduction en phrase :** Pour les contrats qui n’ont pas franchi le dernier palier, je règle le capital à maturité selon la PDI, puis je moyenne les paiements actualisés.

Un contrat traité comme rappelé à la dernière observation a déjà reçu son capital dans la boucle : le masque évite un deuxième versement. Avec spot final 50, strike 100 et PDI 60, un survivant reçoit 0.50 de capital. Les coupons déjà versés restent acquis.

**Finissons l’exemple, jusqu’au prix.** Au deuxième fixing, les prix sont `[90, 95, 50]`, mais `actifs` vaut `[False, True, True]`. A est ignoré ; B franchit le premier palier et reçoit 0.01 ; C ne franchit aucun palier.

Avant le capital final :

```text
flux_actualises = [1.04, 0.03, 0.00]
rappele         = [True, False, False]
```

`S_T = prix[:, n_dates]` lit la dernière colonne, donc `[90, 95, 50]`. `obs_dates[-1]` désigne la dernière date, 1 an. `actualisation_T` vaut 1 dans notre exemple.

`non_rappelees = ~rappele` donne `[False, True, True]`.

Le `np.where` du capital calcule 1 si le prix atteint 60, sinon `S_T / 100` : `[1, 1, 0.50]`. Cette ligne calcule un montant pour chaque scénario ; la ligne suivante ne verse que ceux des survivants. On ajoute donc `[0, 1, 0.50]`.

| Scénario | Coupons et capital finalement comptés |
|---|---:|
| A | 1.04 |
| B | 1.03 |
| C | 0.50 |

`return np.mean(flux_actualises)` renvoie `(1.04 + 1.03 + 0.50) / 3`, soit environ **0.856667**. C’est la moyenne de cet exemple choisi, pas un résultat garanti de la simulation.

Si B atteignait 110 à la dernière observation, le capital serait déjà versé dans la boucle. Le masque final l’empêcherait de le recevoir une deuxième fois.


<a id="dm"></a>
## 8. Double Memory, bloc par bloc

### 8.1 Deux mémoires de nature différente

**Lignes 210–212 de `strutu_engine_pedagogique.py`**

```python
def price_phoenix_dm(S0, r, q, sigma, obs_dates, K_auto, B_phoenix, B_pdi, coupon,
                      n_simulations, dm_version="A", dm_window=3, dm_stat="mean",
                      K_auto_memory=None, memory=True, strike_pct=1.0):
```

**Traduction en phrase :** Je définis un Phoenix avec une mémoire de prix sur plusieurs observations et, si `memory=True`, une mémoire des coupons impayés.

`dm_version="A"` ajoute une condition de rappel fondée sur les prix récents. `"B"` remplace le fixing utilisé pour le coupon par une statistique des prix récents. `dm_window=3` signifie trois observations, pas trois années. `dm_stat="mean"` prend leur moyenne ; `"max"` leur maximum.

**Bien distinguer les options.** Le nom « mémoire » intervient ici dans deux mécanismes :

| Argument | Ce qu’il choisit | Exemple |
|---|---|---|
| `dm_version` | À quoi sert l’historique de prix | A pour aider au rappel ; B pour décider du coupon |
| `dm_window` | Combien de fixings récents regarder | 2 = aujourd’hui et le fixing précédent, lorsqu’il existe |
| `dm_stat` | Comment résumer ces prix | `"mean"` pour moyenne, `"max"` pour maximum |
| `K_auto_memory` | Seuil de rappel appliqué au résumé en A | 0.95 = 95 avec strike 100 |
| `memory` | Garder ou perdre les coupons impayés | `True` garde les montants manqués |

Les guillemets autour de `"A"` ou `"mean"` indiquent du texte. `memory=True` utilise au contraire un booléen, sans guillemets. Modifier une valeur par défaut demande de la préciser lors de l’appel.

Nous suivrons trois trajectoires choisies, avec trois dates, strike 100, taux nul, rappel ponctuel 110, PDI 60, coupon 2 %, fenêtre de 2 observations et moyenne :

```text
           Aujourd’hui   Date 1   Date 2   Date 3
A              100          90      102       85
B              100          70       90       85
C              100          70       50       50
```

Pour la version A, prenons un seuil mémoire de 95 et une barrière coupon de 80. Pour illustrer B séparément plus loin, on prendra une barrière coupon de 85. Ce changement sera indiqué dans le tableau comparatif.


### 8.2 Choisir le seuil de rappel avec mémoire

**Lignes 227–238 de `strutu_engine_pedagogique.py`**

```python
    n_dates = len(obs_dates)
    prix = simulate_observation_dates(S0, r, q, sigma, obs_dates, n_simulations)

    # Par exemple, une barrière de 80 % avec un strike de 100 donne 80.
    strike_reference = strike_pct * S0
    K_auto_level = K_auto * strike_reference
    if K_auto_memory is None:
        K_auto_memory_level = K_auto * strike_reference
    else:
        K_auto_memory_level = K_auto_memory * strike_reference
    B_phoenix_level = B_phoenix * strike_reference
    B_pdi_level = B_pdi * strike_reference
```

**Traduction en phrase :** Je simule les prix et calcule les barrières. Si aucun seuil de rappel avec mémoire n’est fourni, je reprends le seuil de rappel ponctuel.

Avec `K_auto=1.05` et `K_auto_memory=0.95`, la version A peut rappeler grâce à une moyenne supérieure à 95 alors qu’aucun fixing n’a atteint 105. Avec des seuils identiques, cette condition supplémentaire est redondante pour un contrat survivant : un prix assez élevé aurait déjà déclenché le rappel ponctuel.

Cela ne garantit pas l’identité de toutes les conventions avec `price_phoenix` : DM teste aussi le rappel à maturité, alors que Phoenix l’exclut à cette date. `K_auto_memory` n’intervient pas dans la décision de la version B.

**Pourquoi le `if ... is None` ?** On veut autoriser l’appelant à ne pas renseigner de seuil mémoire.

```text
K_auto_memory = None → prendre K_auto comme seuil de remplacement
K_auto_memory = 0.95 → utiliser 0.95
```

`is None` teste l’absence de valeur. Une valeur de zéro n’est pas une absence : elle serait utilisée comme seuil zéro.

Dans notre exemple A, `K_auto_level = 1.10 * 100 = 110` et `K_auto_memory_level = 0.95 * 100 = 95`. `B_phoenix_level` vaut 80 ; `B_pdi_level` vaut 60. Les premières lignes comptent les dates et simulent les prix comme dans Phoenix.

La moyenne n’a pas besoin d’être supérieure au fixing du jour pour ajouter une possibilité de rappel : ici, c’est surtout son seuil **plus bas** qui peut permettre un rappel supplémentaire.


### 8.3 Préparer coupons et état des contrats

**Lignes 241–258 de `strutu_engine_pedagogique.py`**

```python
    if np.isscalar(coupon):
        coupon_schedule = np.full(n_dates, coupon)
    else:
        coupon_schedule = np.asarray(coupon)

    # Au départ, rien n’a encore été versé.
    flux_actualises = np.zeros(n_simulations)
    # False au départ : aucun scénario n’a encore été rappelé.
    rappele = np.zeros(n_simulations, dtype=bool)
    # On garde ici les coupons manqués, séparément pour chaque scénario.
    coupons_en_attente = np.zeros(n_simulations)

    for k in range(1, n_dates + 1):
        t_k = obs_dates[k-1]
        S_k = prix[:, k]
        actualisation = np.exp(-r * t_k)
        # On continue seulement les scénarios qui n’ont pas déjà été remboursés.
        actifs = ~rappele
```

**Traduction en phrase :** Je prépare le calendrier des coupons, les paiements, les rappels et les coupons en attente. À chaque date, je récupère le fixing et les contrats encore vivants.

Ces lignes reprennent les mêmes mécanismes que Phoenix. Le coupon peut être fixe ou une liste ; le stock de coupons est distinct du tableau des prix. Modifier la taille de la fenêtre ne modifie pas directement les montants contractuels des coupons.

**Construisons les valeurs de départ.** `coupon=0.02` est un nombre unique, donc `np.full(3, 0.02)` prépare `[0.02, 0.02, 0.02]`. Avec une liste, `np.asarray` garderait chaque montant fourni, sans répétition automatique.

Les trois tableaux par scénario commencent ainsi :

```text
flux_actualises   = [0, 0, 0]
rappele           = [False, False, False]
coupons_en_attente = [0, 0, 0]
```

Dans `for k in range(1, n_dates + 1)`, `k` vaut 1, puis 2, puis 3. À la première observation :

- `t_k = obs_dates[k-1]` prend la première date de la liste.
- `S_k = prix[:, k]` prend `[90, 70, 70]`, les trois fixings du jour.
- `actualisation = np.exp(-r * t_k)` vaut 1 avec `r=0`.
- `actifs = ~rappele` donne `[True, True, True]`.

Une case de `coupons_en_attente` contient un montant ; une ligne de `prix` contient des prix passés. Ce sont bien deux mémoires différentes.


### 8.4 Construire la fenêtre de prix

**Lignes 262–267 de `strutu_engine_pedagogique.py`**

```python
        debut = max(1, k - dm_window + 1)
        fenetre = prix[:, debut:k+1]
        if dm_stat == "max":
            stat_k = np.max(fenetre, axis=1)
        else:
            stat_k = np.mean(fenetre, axis=1)
```

**Traduction en phrase :** Je sélectionne les dernières observations disponibles, sans le prix initial, puis calcule une moyenne ou un maximum pour chaque trajectoire.

Pour `k=4` et `dm_window=3`, `debut=2` et la tranche `2:5` retient les colonnes 2, 3 et 4. Pour `k=1`, elle ne retient que la colonne 1. Sur `[85, 95, 105]`, la moyenne vaut 95 et le maximum 105.

`axis=1` travaille sur les dates d’un même scénario. Mettre `axis=0` mélangerait les scénarios. Retirer `+1` de la borne de fin exclurait le fixing courant. Le code traite toute valeur autre que `"max"` comme une moyenne : une faute de frappe n’est pas signalée.

**Décortiquons les indices avec une fenêtre de deux observations.**

`max(1, k - dm_window + 1)` prend le plus grand des deux nombres. Il empêche le début de fenêtre de descendre à zéro, car la colonne 0 contient `S0` et non un fixing d’observation.

| `k` | `k - 2 + 1` | `debut` après `max` | Tranche | Colonnes prises |
|---:|---:|---:|---|---|
| 1 | 0 | 1 | `1:2` | 1 |
| 2 | 1 | 1 | `1:3` | 1 et 2 |
| 3 | 2 | 2 | `2:4` | 2 et 3 |

Dans `prix[:, debut:k+1]`, `:` avant la virgule garde tous les scénarios. La partie après la virgule sélectionne les dates. La borne finale est exclue : `k+1` permet donc d’inclure `k`.

À la deuxième observation, notre fenêtre contient :

```text
[[90, 102],
 [70,  90],
 [70,  50]]
```

`np.mean(fenetre, axis=1)` donne `[96, 80, 60]` : on additionne les valeurs de chaque ligne et on divise par deux. `np.max(fenetre, axis=1)` donnerait `[102, 90, 70]`.

Le `if dm_stat == "max"` choisit lequel de ces calculs utiliser. Le double égal compare le texte reçu à `"max"`. Le `else` utilise la moyenne.

**Changer `axis=1` en `axis=0` serait une autre opération** : pour cet exemple, la moyenne deviendrait `[76.6667, 80.6667]`, une valeur par date au lieu d’une valeur par scénario.


### 8.5 Appliquer la version A ou B

**Lignes 270–275 de `strutu_engine_pedagogique.py`**

```python
        if dm_version == "A":
            autocall_now = actifs & ((S_k >= K_auto_level) | (stat_k >= K_auto_memory_level))
            coupon_du = actifs & (S_k >= B_phoenix_level)
        else:
            autocall_now = actifs & (S_k >= K_auto_level)
            coupon_du = actifs & (stat_k >= B_phoenix_level)
```

**Traduction en phrase :** En A, je rappelle si le fixing ou la statistique franchit son seuil, et le coupon dépend du fixing. En B, le rappel dépend du fixing, mais le coupon dépend de la statistique.

Exemple en A : fixing 94, moyenne 96, barrière ponctuelle 105, barrière mémoire 95 → rappel par la moyenne. Exemple en B : fixing 75, moyenne 85, barrière coupon 80 → coupon éligible malgré le fixing de 75.

Le symbole `|` autorise l’une **ou** l’autre condition de rappel en A. Le remplacer par `&` imposerait les deux. Toute version différente de `"A"` suit actuellement le `else`, donc la règle B, même en cas de faute de frappe.

**Version A : deux façons d’être rappelé.** À la première date, les moyennes sont simplement `[90, 70, 70]`. Aucun prix n’atteint 110 et aucune moyenne n’atteint 95 : aucun rappel. Seul A atteint la barrière coupon de 80.

À la deuxième date :

| Scénario | Prix du jour | Moyenne récente | Prix ≥ 110 ? | Moyenne ≥ 95 ? | Rappel A ? |
|---|---:|---:|---|---|---|
| A | 102 | 96 | Non | Oui | Oui |
| B | 90 | 80 | Non | Non | Non |
| C | 50 | 60 | Non | Non | Non |

Dans `actifs & ((condition1) | (condition2))`, les parenthèses regroupent les deux possibilités de rappel. Le `|` accepte l’une ou l’autre ; le `&` exige en plus que le contrat soit actif.

**Version B : le coupon suit la moyenne.** Pour voir une différence nette, prenons une barrière coupon de 85. À la deuxième date, B a un fixing de 90 mais une moyenne de 80 : il ne reçoit pas encore son coupon. À la troisième, sa moyenne vaut `(90 + 85) / 2 = 87.5` : il devient éligible.

Le rappel de B reste fondé sur le prix du jour et le seuil 110. La ligne `coupon_du = actifs & (stat_k >= B_phoenix_level)` remplace seulement la condition de coupon. Si `memory=True`, ce coupon éligible pourra rattraper les coupons manqués.

À la dernière observation aussi, ce moteur teste le rappel. Il ne possède pas le test `k < n_dates` du Phoenix précédent.


### 8.6 Mémoire des coupons et versements

**Lignes 277–293 de `strutu_engine_pedagogique.py`**

```python
        coupon_periode = coupon_schedule[k-1]
        if memory:
            # Le coupon du jour s’ajoute à ceux qu’on n’a pas encore payés.
            coupons_en_attente += np.where(actifs, coupon_periode, 0.0)
            montant_coupon = np.where(coupon_du, coupons_en_attente, 0.0)
            # Si on vient de payer, il n’y a plus de coupons en attente.
            coupons_en_attente = np.where(coupon_du, 0.0, coupons_en_attente)
        else:
            # Sans mémoire, on ne rattrape pas les coupons manqués.
            montant_coupon = np.where(coupon_du, coupon_periode, 0.0)

        # On paie le coupon dû, même si le produit est rappelé aujourd’hui.
        flux_actualises += montant_coupon * actualisation
        # En cas de rappel, on rend aussi le capital : 1 = 100 % du nominal.
        flux_actualises += np.where(autocall_now, 1.0 * actualisation, 0.0)

        rappele = rappele | autocall_now
```

**Traduction en phrase :** Une fois l’éligibilité décidée, je calcule les coupons à verser, vide la mémoire payée, ajoute les paiements actualisés et ferme les contrats rappelés.

La mémoire monétaire fonctionne comme dans Phoenix : coupons successifs de 1 % puis 3 %, premier paiement refusé et second accepté → 4 % avec mémoire, 3 % sans mémoire. `memory=False` désactive ce rattrapage, mais **ne désactive pas la fenêtre de prix** du Double Memory.

**Suivons les montants de la version A.** Le premier coupon prévu vaut `coupon_schedule[0] = 0.02`.

1. `coupons_en_attente += np.where(actifs, coupon_periode, 0.0)` ajoute 0.02 à chaque scénario actif : le stock devient `[0.02, 0.02, 0.02]`.
2. `montant_coupon = np.where(coupon_du, coupons_en_attente, 0.0)` décide du paiement. Seul A est éligible : `[0.02, 0, 0]`.
3. `coupons_en_attente = np.where(coupon_du, 0.0, coupons_en_attente)` vide la case payée : `[0, 0.02, 0.02]`.
4. La première ligne sur les flux ajoute le coupon actualisé ; la deuxième ajoute le capital uniquement si le rappel a lieu.
5. `rappele | autocall_now` conserve l’historique des contrats terminés.

| Après l’observation | Paiements cumulés A / B / C | Coupons en attente A / B / C | Rappelés A / B / C |
|---|---|---|---|
| 1 | `[0.02, 0, 0]` | `[0, 0.02, 0.02]` | `[False, False, False]` |
| 2 | `[1.04, 0.04, 0]` | `[0, 0, 0.04]` | `[True, False, False]` |
| 3 | `[1.04, 0.06, 0]` | `[0, 0, 0.06]` | `[True, False, False]` |

Au deuxième tour, A reçoit son coupon de 2 % et son capital ; B reçoit les deux coupons de 2 % ; C ne touche rien. Au troisième, A ne reçoit plus rien.

Avec `memory=False`, la branche `else` choisit le seul coupon du jour au lieu du stock. Elle ne supprime pas les calculs de moyenne ou maximum des prix.


### 8.7 Capital final et prix du DM

**Lignes 295–304 de `strutu_engine_pedagogique.py`**

```python
    S_T = prix[:, n_dates]
    actualisation_T = np.exp(-r * obs_dates[-1])
    non_rappelees = ~rappele
    # À la barrière ou au-dessus, on rend tout le capital.
    # En dessous, on rembourse S_T / strike : par exemple 50 / 100 = 50 %.
    remboursement_T = np.where(S_T >= B_pdi_level, 1.0, S_T / strike_reference)
    flux_actualises += np.where(non_rappelees, remboursement_T * actualisation_T, 0.0)

    # On fait la moyenne de ce qui a été payé dans tous les scénarios.
    return np.mean(flux_actualises)
```

**Traduction en phrase :** Je rembourse les survivants selon le prix final et la barrière PDI, puis calcule leur contribution au prix moyen.

La statistique de fenêtre ne remplace pas `S_T` pour la protection finale. Un prix final inférieur à la PDI peut donc entraîner une perte même si la moyenne récente est meilleure, tant que le contrat n’a pas été rappelé. Il n’y a pas d’argument de bonus dans cette fonction.

**Calcul final de la version A.** `S_T` vaut `[85, 85, 50]`. L’inverse de `rappele` donne `[False, True, True]`. La PDI finale regarde ces fixings, pas leur moyenne : les remboursements calculés sont `[1, 1, 0.50]`.

La ligne d’ajout final applique le filtre des survivants. Elle ajoute `[0, 1, 0.50]` aux paiements déjà enregistrés :

```text
flux_actualises final = [1.04, 1.06, 0.50]
prix moyen = (1.04 + 1.06 + 0.50) / 3 = 0.866666...
```

**Comparaison avec B dans notre second exemple** (barrière coupon 85, toujours avec mémoire) : A ne franchit jamais le rappel ponctuel de 110 et reçoit trois coupons, puis son capital. B manque les deux premières conditions de coupon, puis sa moyenne de 87.5 lui permet de toucher 6 % à la troisième date. C finit à 50 sans coupon.

| Variante illustrative | Total A | Total B | Total C | Moyenne |
|---|---:|---:|---:|---:|
| A, barrière coupon 80, rappel mémoire 95 | 1.04 | 1.06 | 0.50 | 0.866667 |
| B, barrière coupon 85 | 1.06 | 1.06 | 0.50 | 0.873333 |

Ces montants sont vérifiables sur les trajectoires choisies. Ils expliquent le mécanisme et ne sont pas une comparaison commerciale à paramètres identiques.

`return` renvoie la moyenne au programme appelant. Ni les tableaux de détail ni la fréquence des rappels ne sont renvoyés par cette fonction.


<a id="japan"></a>
## 9. Japan 2, bloc par bloc

### 9.1 Paramètres particuliers

**Lignes 309–311 de `strutu_engine_pedagogique.py`**

```python
def price_phoenix_japan2(S0, r, q, sigma, T, obs_dates,
                          K_auto, B_coupon_low, B_pdi, coupon,
                          n_simulations, strike_pct=1.0, trading_days_per_year=252):
```

**Traduction en phrase :** Je définis un produit avec une maturité explicite, une grille journalière, des coupons proportionnels aux jours éligibles et une barrière de protection surveillée pendant la vie du contrat.

`T` définit la fin de simulation. `obs_dates` définit les dates de versement et de rappel. `trading_days_per_year=252` fixe une densité de grille ; il ne charge pas un calendrier réel de jours fériés. Le coupon est ici un montant scalaire maximal par période.

**Notre petit calendrier pour voir les tableaux.** Nous utiliserons une grille fictive de quatre jours sur un an : `T=1`, `trading_days_per_year=4`, avec observations à `[0.5, 1.0]`. C’est uniquement pour rendre l’exemple lisible ; l’usage courant du fichier est une grille bien plus fine.

Prenons `S0=100`, strike 100, taux nul, rappel à 100, barrière coupon à 80, PDI à 60 et coupon plein de 4 % par période. Les trois trajectoires choisies sont :

```text
           Jour 0   Jour 1   Jour 2   Jour 3   Jour 4
A            100       90      105       50       90
B            100       70       90       85       90
C            100       55       70       85       90
```

Les jours 2 et 4 sont les observations de rappel et de paiement. Les jours intermédiaires servent au coupon et à la surveillance de la PDI.

`B_coupon_low` est une fraction du strike, malgré son nom différent de `B_phoenix`. `coupon=0.04` est le montant maximal d’une période ; la fraction de jours éligibles déterminera combien est réellement versé.


### 9.2 Simuler chaque jour de la grille

**Lignes 324–331 de `strutu_engine_pedagogique.py`**

```python
    n_days = int(round(T * trading_days_per_year))
    dt = T / n_days

    prix = np.zeros((n_simulations, n_days + 1))
    prix[:, 0] = S0
    for i in range(1, n_days + 1):
        Z = np.random.normal(0, 1, n_simulations)
        prix[:, i] = prix[:, i-1] * np.exp((r - q - sigma**2/2)*dt + sigma*np.sqrt(dt)*Z)
```

**Traduction en phrase :** Je calcule un nombre entier de jours, répartis ces pas sur la durée T et simule le prix à chacun de ces points.

Pour `T=1`, il y a 252 pas, `dt=1/252` et 253 colonnes avec aujourd’hui. Pour `T=0.5`, il y a 126 pas. `round` arrondit au plus proche ; aux demi-entiers exacts, Python arrondit vers l’entier pair. `int` transforme ensuite en entier.

Le calcul est plus volumineux qu’une simulation trimestrielle. Avec 10 000 scénarios et 253 colonnes de nombres sur 8 octets, le seul tableau `prix` occupe environ 20 Mo. Si la durée donne `n_days=0`, la division échoue.

**Construisons la grille ligne par ligne.**

- `T * trading_days_per_year` vaut `1 * 4 = 4`.
- `round(...)` arrondit au plus proche et `int(...)` donne un entier : `n_days=4`.
- `dt = T / n_days` donne `0.25` an entre deux colonnes.
- `np.zeros((n_simulations, n_days + 1))` crée ici 3 lignes et 5 colonnes.
- `prix[:, 0] = S0` place 100 dans la première colonne de chaque ligne.

Avant simulation :

```text
[[100, 0, 0, 0, 0],
 [100, 0, 0, 0, 0],
 [100, 0, 0, 0, 0]]
```

`for i in range(1, n_days + 1)` parcourt 1, 2, 3 et 4. Ici, `i` est un jour de grille. `np.random.normal(0, 1, n_simulations)` tire trois chocs par jour, un pour chaque scénario.

La longue ligne de simulation dit : « pour remplir la colonne i, prends le prix de la colonne i-1 et applique la croissance et le choc de cette durée ». Elle utilise la même formule que la première fonction du fichier, mais avec une durée constante `dt`.

Au premier tour on lit la colonne 0 pour remplir la colonne 1 ; au dernier on lit la colonne 3 pour remplir la colonne 4. Supprimer le `+1` de la taille du tableau laisserait manquer cette dernière colonne.


### 9.3 Niveaux et suivi de la PDI

**Lignes 334–342 de `strutu_engine_pedagogique.py`**

```python
    strike_reference = strike_pct * S0
    K_auto_level = K_auto * strike_reference
    B_coupon_level = B_coupon_low * strike_reference
    B_pdi_level = B_pdi * strike_reference

    # Un seul jour sur la barrière ou en dessous suffit, même à la date 0.
    # On ne voit pas les passages entre deux jours de la grille.
    # Ce test ne servira qu’aux contrats qui vont jusqu’au remboursement final.
    pdi_touchee = (prix <= B_pdi_level).any(axis=1)
```

**Traduction en phrase :** Je calcule les niveaux de prix, puis je demande pour chaque trajectoire si le sous-jacent a atteint ou traversé la barrière PDI au moins une fois.

Pour une barrière de 60, la trajectoire `[100, 58, 105]` active la PDI malgré son rebond. L’égalité active aussi la barrière à cause de `<=`. Le tableau comprend `S0`, donc un départ sur la barrière l’active immédiatement.

`.any(axis=1)` ne compte pas les jours : un seul suffit. La surveillance est journalière sur la grille, pas continue entre deux points. Tester toute la trajectoire à l’avance ne décide pas le rappel avec une information future : ce résultat sert uniquement au capital final des contrats non rappelés.

**Les barrières.** Les quatre multiplications préparent respectivement le strike 100, le rappel 100, la barrière coupon 80 et la PDI 60. Comparer le tableau des prix directement à `0.60` serait une erreur d’unité.

**Le test de PDI en deux opérations.** `(prix <= B_pdi_level)` compare chaque case à 60 :

```text
A : [False, False, False, True,  False]
B : [False, False, False, False, False]
C : [False, True,  False, False, False]
```

Puis `.any(axis=1)` demande, ligne par ligne : « y a-t-il au moins un True ? »

```text
pdi_touchee = [True, False, True]
```

`axis=1` résume les jours de chaque scénario. Sans cet argument, `.any()` donnerait une seule réponse pour le tableau entier et ferait perdre la distinction entre contrats.

A touche 60 ou moins après son rappel au jour 2. Cela n’annule pas ce rappel : ce test ne servira qu’aux survivants. B ne touche jamais la PDI. C la touche au jour 1 et conserve cette information malgré son rebond à 90.

`<=` inclut l’égalité. Un départ à la barrière activerait aussi la PDI, car la colonne 0 fait partie du tableau testé.


### 9.4 Convertir les observations en jours

**Lignes 345–352 de `strutu_engine_pedagogique.py`**

```python
    flux_actualises = np.zeros(n_simulations)
    # False au départ : aucun scénario n’a encore été rappelé.
    rappele = np.zeros(n_simulations, dtype=bool)

    obs_days = []
    for t in obs_dates:
        jour_observation = int(round(t / dt))
        obs_days.append(jour_observation)
```

**Traduction en phrase :** Je prépare les paiements et les rappels, puis transforme chaque date d’observation en position sur la grille journalière.

Avec `dt=1/252`, la date `0.25` donne le jour 63. Les dates sont arrondies, mais l’actualisation restera calculée à la date contractuelle. Deux dates très proches peuvent tomber sur le même jour : la seconde période aurait alors zéro jour, ce que le code ne protège pas.

**Initialisation.** Les flux commencent à `[0, 0, 0]` et les rappels à `[False, False, False]`. Il n’y a pas de tableau de coupons en attente : ce Japan 2 calcule un coupon à partir de la proportion de jours de chaque période.

`obs_days = []` crée une liste vide. La boucle `for t in obs_dates` prend directement les dates 0.5 puis 1.0, pas leurs indices.

| `t` | `t / dt` avec `dt=0.25` | Jour obtenu | Liste après `.append` |
|---:|---:|---:|---|
| 0.5 | 2 | 2 | `[2]` |
| 1.0 | 4 | 4 | `[2, 4]` |

Diviser une date en années par la durée d’un pas donne le nombre de pas depuis aujourd’hui. `round` choisit un point de grille et `int` en fait un indice entier. `.append` ajoute cet indice à la fin de la liste.

Le nombre 2 représente ici le **jour 2 de la grille**, pas la deuxième case de la liste : la première case de `obs_days` contient 2.


### 9.5 Délimiter chaque période

**Lignes 354–360 de `strutu_engine_pedagogique.py`**

```python
    jour_debut_periode = 0
    for k in range(len(obs_days)):
        jour_fin = obs_days[k]
        t_k = obs_dates[k]
        actualisation = np.exp(-r * t_k)
        # On continue seulement les scénarios qui n’ont pas déjà été remboursés.
        actifs = ~rappele
```

**Traduction en phrase :** Je commence après aujourd’hui et, pour chaque observation, récupère son jour de fin, sa date contractuelle et les contrats encore actifs.

Ici `k` commence à 0 : `obs_days[k]` et `obs_dates[k]` ont les mêmes positions. Le fixing sera lu avec `jour_fin`, pas avec `k`. Confondre ces indices sélectionnerait un des tout premiers jours au lieu de la date d’observation.

**Premier tour de paiement.** `jour_debut_periode=0` place le début à aujourd’hui. `len(obs_days)=2`, donc `range(len(obs_days))` produit 0 puis 1.

| Ligne | Premier tour (`k=0`) | Deuxième tour (`k=1`) |
|---|---|---|
| `jour_fin = obs_days[k]` | 2 | 4 |
| `t_k = obs_dates[k]` | 0.5 | 1.0 |
| `actualisation = np.exp(-r * t_k)` | 1 avec taux nul | 1 avec taux nul |

`actifs = ~rappele` commence à `[True, True, True]`. Après le rappel de A au premier tour, il deviendra `[False, True, True]` au second.

Ici il n’y a pas de `k-1`, car `k` commence à zéro et indexe deux listes sans colonne initiale supplémentaire. Le tableau des prix sera indexé avec le numéro de jour `jour_fin`.


### 9.6 Calculer le coupon proportionnel

**Lignes 362–367 de `strutu_engine_pedagogique.py`**

```python
        periode = prix[:, jour_debut_periode+1:jour_fin+1]
        n_jours_periode = periode.shape[1]
        jours_au_dessus = (periode >= B_coupon_level).sum(axis=1)
        # Par exemple, 15 jours sur 20 donnent droit à 75 % du coupon plein.
        fraction = jours_au_dessus / n_jours_periode
        montant_coupon = fraction * coupon
```

**Traduction en phrase :** Je prends les jours de la période, compte ceux où la condition de coupon est satisfaite et verse la fraction correspondante du coupon plein.

Une première période finissant au jour 63 prend les jours 1 à 63 ; la suivante commence au jour 64. La borne initiale exclut le fixing déjà compté dans la période précédente. La borne finale inclut le jour d’observation.

Sur 20 jours, 15 jours éligibles et un coupon plein de 4 % donnent `15/20 × 0.04 = 0.03`, soit 3 %. `shape[1]` fournit les 20 jours ; `shape[0]` donnerait le nombre de scénarios et serait faux. Les coupons sont payés en fin de période : ils ne sont pas actualisés jour par jour.

**Découpons la première période.**

`periode = prix[:, jour_debut_periode+1:jour_fin+1]` devient `prix[:, 1:3]`. On conserve toutes les lignes et les colonnes 1 et 2 :

```text
periode = [[90, 105],
           [70,  90],
           [55,  70]]
```

La borne finale 3 est exclue. Le début à 1 exclut aujourd’hui. Au prochain tour, on prendra les jours 3 et 4 : le jour 2 ne doit pas être compté deux fois.

`periode.shape` donne `(3, 2)` : trois scénarios, deux jours. `periode.shape[1]` lit le deuxième nombre, donc `n_jours_periode=2`. Le `[1]` est un indice, pas un nombre de jours demandé.

La comparaison `periode >= 80` donne :

```text
[[True,  True],
 [False, True],
 [False, False]]
```

`.sum(axis=1)` compte les jours éligibles de chaque ligne : `[2, 1, 0]`, puisque `True` compte comme 1 et `False` comme 0.

| Étape | A | B | C |
|---|---:|---:|---:|
| `jours_au_dessus` | 2 | 1 | 0 |
| `fraction = jours_au_dessus / n_jours_periode` | 1 | 0.5 | 0 |
| `montant_coupon = fraction * coupon` | 0.04 | 0.02 | 0 |

Le coupon est payé à la fin de la période. Un jour non éligible réduit sa fraction ; il n’est pas gardé comme un coupon impayé à récupérer plus tard.


### 9.7 Coupon acquis et remboursement au rappel

**Lignes 369–378 de `strutu_engine_pedagogique.py`**

```python
        S_k = prix[:, jour_fin]
        # Ici aussi, le rappel est testé à la dernière observation.
        autocall_now = actifs & (S_k >= K_auto_level)

        # On verse le coupon accumulé sur la période aux contrats encore en vie.
        flux_actualises += np.where(actifs, montant_coupon * actualisation, 0.0)
        flux_actualises += np.where(autocall_now, 1.0 * actualisation, 0.0)

        rappele = rappele | autocall_now
        jour_debut_periode = jour_fin
```

**Traduction en phrase :** Je regarde le fixing de fin de période, verse le coupon acquis aux contrats actifs, rembourse ceux rappelés et prépare le début de la période suivante.

Le rappel est testé aux dates de `obs_dates`, pas tous les jours. Une hausse au-dessus de la barrière entre deux observations ne suffit pas. Le coupon dépend des jours de la période ; le rappel dépend du fixing de fin. Comme dans Zenith et DM, le test est effectué aussi à la dernière observation.

Oublier `jour_debut_periode = jour_fin` ferait recompter les jours depuis aujourd’hui à chaque coupon.

**Regardons le rappel après ce calcul de coupon.** `S_k = prix[:, jour_fin]` lit la colonne 2, donc `[105, 90, 70]`. Le test `actifs & (S_k >= 100)` donne `[True, False, False]`.

La première ligne d’ajout choisit `montant_coupon * actualisation` pour les actifs et zéro sinon. La seconde ajoute 1 actualisé aux seuls rappels. Avec notre taux nul :

```text
Après coupon :  [0.04, 0.02, 0.00]
Après capital : [1.04, 0.02, 0.00]
rappele :       [True, False, False]
```

`rappele = rappele | autocall_now` conserve ces décisions. `jour_debut_periode = jour_fin` met le début à 2 pour le prochain tour.

**Deuxième période : jours 3 et 4.** Les valeurs sont `[[50, 90], [85, 90], [85, 90]]`. Les fractions éligibles valent `[0.5, 1, 1]`, donc les coupons calculés sont `[0.02, 0.04, 0.04]`.

Mais A n’est plus actif. Le filtre de paiement transforme son coupon calculé en zéro à verser. Les prix de fin valent tous 90, donc aucun nouveau rappel. Les flux deviennent :

```text
[1.04, 0.06, 0.04]
```

Calculer une valeur dans un tableau ne signifie donc pas automatiquement la payer : le masque `actifs` garde cette distinction.


### 9.8 Capital après une barrière touchée

**Lignes 380–390 de `strutu_engine_pedagogique.py`**

```python
    non_rappelees = ~rappele
    S_T = prix[:, n_days]
    actualisation_T = np.exp(-r * T)

    # Si la PDI a été touchée, on regarde la perte par rapport au strike.
    # Même après un rebond, on ne rembourse pas plus de 100 % du capital.
    remboursement_T = np.where(pdi_touchee & non_rappelees, np.minimum(S_T / strike_reference, 1.0), 1.0)
    flux_actualises += np.where(non_rappelees, remboursement_T * actualisation_T, 0.0)

    # On fait la moyenne de ce qui a été payé dans tous les scénarios.
    return np.mean(flux_actualises)
```

**Traduction en phrase :** Pour les contrats non rappelés, je rembourse 1 si la PDI n’a jamais été touchée. Si elle l’a été, je verse le ratio du prix final au strike, plafonné à 1. J’actualise ce capital à T et renvoie le prix moyen.

Avec strike 100 et PDI touchée : prix final 50 → capital 0.50 ; prix final 90 → 0.90 ; prix final 110 → 1.00 grâce au plafond. Sans PDI touchée, le capital reste 1. Les coupons déjà acquis s’ajoutent à ces montants.

Retirer `np.minimum(..., 1.0)` autoriserait un capital supérieur à 100 % après un rebond. Si la dernière observation est avant T, le code paie le capital à T mais ne crée pas automatiquement un coupon pour la période restante.

**Terminons l’exemple ligne par ligne.**

`non_rappelees = ~rappele` donne `[False, True, True]`. `S_T = prix[:, n_days]` prend les prix du dernier jour : `[90, 90, 90]`. `actualisation_T = np.exp(-r * T)` vaut 1.

La ligne de remboursement est longue, mais on peut la lire en trois morceaux :

1. `pdi_touchee & non_rappelees` identifie les survivants ayant touché la barrière : `[False, False, True]`.
2. `np.minimum(S_T / strike_reference, 1.0)` calcule les ratios en les plafonnant à 1 : ici `[0.90, 0.90, 0.90]`.
3. `np.where(condition, ratio_plafonne, 1.0)` choisit le ratio si la condition est vraie, sinon 1 : `[1.00, 1.00, 0.90]`.

B et C ont le même prix final, mais **pas le même remboursement**. B n’a jamais touché la PDI ; C est passé à 55 en cours de vie. Le passé intervient dans ce produit.

Le montant 1 calculé pour A ne sera pas versé : la ligne suivante ajoute seulement les montants des `non_rappelees`, soit `[0, 1, 0.90]`.

| Scénario | Flux avant capital final | Capital ajouté à maturité | Total |
|---|---:|---:|---:|
| A | 1.04 | 0 | 1.04 |
| B | 0.06 | 1.00 | 1.06 |
| C | 0.04 | 0.90 | 0.94 |

`return np.mean(flux_actualises)` donne `(1.04 + 1.06 + 0.94) / 3`, soit environ **1.013333** pour nos trajectoires illustratives.

Pour comprendre le plafond, imaginons séparément un survivant avec PDI touchée, strike 100, prix final 110 et barrière de rappel suffisamment haute pour qu’il survive : le ratio vaut 1.10 mais `np.minimum(1.10, 1.0)` garde 1. Le remboursement de capital ne participe pas à la hausse au-delà du nominal.

Ce calcul utilise T pour le capital et les dates d’observation pour les coupons. Si la dernière observation est avant T, le code ne crée pas automatiquement une dernière période de coupon.


<a id="appels"></a>
## 10. Choisir les arguments de chaque produit

### 10.1 Les variantes Phoenix

Repars de l’appel complet de la section 1 et modifie les arguments indiqués. Chaque ligne ci-dessous décrit un réglage ; ce ne sont pas des fonctions supplémentaires.

| Produit souhaité | Arguments à utiliser |
|---|---|
| Standard sans mémoire | `memory=False` |
| Memory | `memory=True` |
| Bonus final | `bonus_threshold=1.0, bonus_amount=0.05` |
| Step-up sur 4 dates | `coupon=[0.01, 0.02, 0.03, 0.04]` |
| Sans autocall | `has_autocall=False` |
| Custom strike à 90 % | `strike_pct=0.90` |

Ces options sont combinables. Pour un step-up **sans** mémoire, il faut aussi écrire `memory=False` : fournir une liste ne change pas le défaut de mémoire.

### 10.2 Trois autres appels complets

Ce code peut être placé dans un second fichier à côté du moteur :

```python
import numpy as np
from strutu_engine_pedagogique import (
    price_zenith,
    price_phoenix_dm,
    price_phoenix_japan2,
)

np.random.seed(42)

zenith = price_zenith(
    S0=100, r=0.03, q=0.01, sigma=0.20,
    obs_dates=[0.25, 0.50, 0.75, 1.00],
    K_levels=[0.80, 1.00, 1.10],
    C_levels=[0.01, 0.02, 0.04],
    B_pdi=0.60, n_simulations=10000,
)

double_memory = price_phoenix_dm(
    S0=100, r=0.03, q=0.01, sigma=0.20,
    obs_dates=[0.25, 0.50, 0.75, 1.00],
    K_auto=1.05, B_phoenix=0.80, B_pdi=0.60,
    coupon=0.02, n_simulations=10000,
    dm_version="A", dm_window=3, dm_stat="mean",
    K_auto_memory=0.95, memory=True,
)

japan = price_phoenix_japan2(
    S0=100, r=0.03, q=0.01, sigma=0.20,
    T=1.00, obs_dates=[0.25, 0.50, 0.75, 1.00],
    K_auto=1.00, B_coupon_low=0.80, B_pdi=0.60,
    coupon=0.02, n_simulations=10000,
    trading_days_per_year=252,
)

print("Zenith :", zenith)
print("Double Memory A :", double_memory)
print("Japan 2 :", japan)
```

**Traduction en phrase :** Je valorise successivement un Zenith à trois paliers, un Double Memory A avec fenêtre de trois observations et un Japan 2 observé sur une grille journalière.

Pour étudier la version B, remplace `dm_version="A"` par `dm_version="B"`. `K_auto_memory` sera alors ignoré dans les conditions de paiement. Pour prendre le maximum récent, remplace `dm_stat="mean"` par `dm_stat="max"`.

### 10.3 Tableau des conventions réellement codées

| Règle | Phoenix | Zenith | Double Memory | Japan 2 |
|---|---|---|---|---|
| Mémoire de coupons | Optionnelle, active par défaut | Non | Optionnelle, active par défaut | Non |
| Coupon variable selon la date | Liste possible | Coupons selon les paliers | Liste possible | Coupon plein scalaire |
| Condition coupon | Fixing | Plus haut palier franchi | Fixing en A, statistique en B | Fraction de jours éligibles |
| Protection du capital | Prix final | Prix final | Prix final | Barrière touchée sur la grille |
| Test de rappel à la dernière observation | Non | Oui | Oui | Oui |
| Bonus final dédié | Oui | Non | Non | Non |
| Maturité utilisée pour le capital | Dernière observation | Dernière observation | Dernière observation | `T` explicite |

Pour une PDI finale, égalité à la barrière = capital protégé. Pour la PDI Japan 2, égalité = barrière touchée. Cette différence vient de `>=` dans le premier cas et `<=` dans le second.

<a id="oral"></a>
## 11. Limites, vérifications et questions d’oral

### 11.1 Entrées à préparer correctement

Le fichier est volontairement simple et ne possède pas une couche complète de validation. Avant un appel :

- Utiliser des nombres finis, `S0 > 0`, `strike_pct > 0`, `sigma >= 0` et un nombre entier de simulations strictement positif.
- Fournir une liste non vide de dates strictement croissantes et positives. Phoenix, Zenith et DM déduisent la maturité de la dernière date.
- Fournir autant de coupons que de dates lorsqu’une liste est utilisée.
- Pour Zenith, fournir des listes de paliers et coupons non vides de même longueur, avec des barrières strictement croissantes et des coupons cohérents avec le contrat.
- Pour DM, utiliser exactement `"A"` ou `"B"`, `"mean"` ou `"max"`, et une fenêtre entière strictement positive.
- Pour Japan 2, choisir `T > 0`, un nombre de jours annuel positif et une grille comportant au moins un pas. Les observations doivent tomber sur des jours distincts, compris entre 1 et `n_days`. Mettre la dernière observation à `T` si les coupons doivent couvrir toute la durée.

Les barrières sont des fractions du strike. Le moteur ne vérifie pas leur cohérence économique. Par exemple, le remboursement final des trois premiers moteurs n’est pas explicitement plafonné dans sa branche `S_T / strike_reference` : avec une PDI supérieure au strike, des paramètres inhabituels pourraient produire un capital supérieur à 1 dans cette branche. Le guide décrit le comportement existant, sans le modifier.

### 11.2 Ce que le modèle ne calcule pas

Il utilise un seul sous-jacent, des paramètres constants et un mouvement brownien géométrique. Il ne modélise ni défaut de l’émetteur, ni frais, ni financement spécifique, ni volatilité locale ou stochastique, ni sauts. Il ne récupère pas de marché en direct et ne calibre pas `sigma`.

Le retour est un seul prix moyen : pas de décomposition des flux, de probabilités de rappel, de sensibilités ni d’intervalle de confiance. Japan 2 utilise une approximation journalière de la surveillance de barrière : un franchissement entre deux points peut ne pas être détecté.

### 11.3 Reproductibilité et précision

`np.random.seed(42)` fixe l’état des tirages avant un calcul. Le nombre 42 n’a aucune signification financière. Relancer deux appels l’un après l’autre sans réinitialiser la graine utilise des tirages différents.

Plus de simulations réduit généralement l’incertitude Monte-Carlo, sans corriger une mauvaise formule ou de mauvais paramètres. L’ordre de grandeur de l’erreur statistique décroît comme `1 / sqrt(N)` : multiplier le nombre de scénarios par quatre divise approximativement l’erreur-type par deux.

### 11.4 Contrôle simple que tu peux refaire

```python
import numpy as np
from strutu_engine_pedagogique import price_phoenix

prix = price_phoenix(
    S0=100, r=0, q=0, sigma=0,
    obs_dates=[0.5, 1.0],
    K_auto=1.0, B_phoenix=0.8, B_pdi=0.6,
    coupon=0.03, n_simulations=10,
    memory=True, has_autocall=False,
    bonus_threshold=1.0, bonus_amount=0.05,
)

print(prix)
assert np.isclose(prix, 1.11)
```

**Traduction en phrase :** Je supprime tout hasard et toute actualisation. Le spot reste à 100, les deux coupons de 3 % sont versés, puis le capital de 1 et le bonus de 5 %. Je vérifie donc `1 + 0.03 + 0.03 + 0.05 = 1.11`.

`np.isclose` accepte les minuscules écarts dus à la représentation des nombres décimaux. Un test d’égalité stricte avec `==` serait inutilement fragile.

Lors de la création du moteur, la syntaxe et les signatures ont été vérifiées ; 48 comparaisons avec le moteur original à tirages identiques et 3 contrôles déterministes ont réussi. Ces comparaisons contrôlent la conservation des résultats sur les cas testés ; elles ne constituent pas une certification de tous les contrats possibles.

### 11.5 Questions à préparer pour un oral

**Pourquoi plusieurs trajectoires ?** Un produit peut verser à plusieurs dates et s’arrêter tôt. Chaque trajectoire permet de déterminer les paiements correspondant à une évolution complète du sous-jacent.

**Pourquoi une boucle sur les dates, mais pas sur les scénarios ?** La chronologie est séquentielle. NumPy traite simultanément tous les scénarios d’une même date, grâce aux tableaux et aux masques.

**Pourquoi actualiser chaque coupon séparément ?** Un montant reçu tôt et le même montant reçu tard n’ont pas la même valeur aujourd’hui.

**Pourquoi le drift est-il `r-q` ?** On simule sous la mesure risque-neutre pour valoriser les paiements. Ce n’est pas une prévision du rendement historique de l’action.

**Comment évites-tu de payer après un rappel ?** `rappele` garde les contrats terminés ; `actifs = ~rappele` les exclut des décisions futures ; `non_rappelees` les exclut du capital final.

**Est-ce que memory garantit tous les coupons ?** Non. Elle permet leur rattrapage si la condition de coupon est ensuite satisfaite. Un stock impayé à la fin peut rester perdu.

**Quelle différence entre les deux mémoires du DM ?** L’une conserve des montants de coupons ; l’autre regarde plusieurs prix passés pour décider une condition de paiement ou de rappel.

**Le Zenith cumule-t-il tous les paliers franchis ?** Non : il conserve seulement le coupon du plus haut palier atteint. Seul le dernier palier déclenche aussi le remboursement.

**Pourquoi plafonner le capital Japan 2 après un rebond ?** Le mécanisme codé rend le capital exposé à la baisse après activation de la PDI, mais ne donne pas de participation à la hausse au-delà du nominal.

**Un prix de 1.02 signifie-t-il 2 % de rendement ?** Non. C’est la valeur actuelle estimée de tous les flux pour un nominal de 1. Un rendement d’investissement dépend aussi du prix réellement payé, des dates et des flux réalisés.

**Que prouve la comparaison avec l’original ?** Elle montre que la réécriture conserve les résultats des scénarios testés, à l’arrondi numérique près. Un accord entre deux programmes ne prouve pas à lui seul que la convention correspond au term sheet souhaité.

