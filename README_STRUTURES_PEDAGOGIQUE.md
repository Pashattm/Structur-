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

**Lignes 45–52 de `strutu_engine_pedagogique.py`**

```python
import numpy as np


# =========================
# Simulation aux dates d'observation
# =========================

def simulate_observation_dates(S0, r, q, sigma, obs_dates, n_simulations):
```

**Traduction en phrase :** Je charge NumPy sous le nom court `np`, puis je définis la fonction qui construira les prix à chaque observation.

`S0`, `r`, `q`, `sigma`, les dates et le nombre de simulations sont fournis par l’appelant. Cette fonction simule le marché : elle ne connaît ni les coupons ni les barrières. Changer le nom de la fonction sans adapter ses appels casserait les fonctions de pricing.

### 5.2 Préparer les trajectoires

**Lignes 60–66 de `strutu_engine_pedagogique.py`**

```python
    n_dates = len(obs_dates)
    prix = np.zeros((n_simulations, n_dates + 1))
    prix[:, 0] = S0

    # Une ligne = un scénario ; une colonne = une date.
    # Le prix initial est connu et identique dans tous les scénarios.
    t_precedent = 0
```

**Traduction en phrase :** Je compte les observations, prépare un tableau de prix, place le prix initial dans la première colonne et mémorise que nous partons de la date zéro.

Pour 2 scénarios et 4 observations, la forme est `(2, 5)`. Le `+1` réserve aujourd’hui. Sans lui, la dernière colonne manquerait. `np.zeros` prépare l’espace ; ses zéros ne sont pas des prix simulés définitifs.

### 5.3 Avancer de date en date

**Lignes 67–78 de `strutu_engine_pedagogique.py`**

```python
    for i in range(n_dates):
        t = obs_dates[i]
        dt = t - t_precedent
        # Un choc aléatoire indépendant pour chaque scénario.
        Z = np.random.normal(0, 1, n_simulations)
        # Croissance risque-neutre et choc de volatilité sur la période.
        croissance = (r - q - sigma**2 / 2) * dt
        choc = sigma * np.sqrt(dt) * Z
        prix[:, i+1] = prix[:, i] * np.exp(croissance + choc)
        t_precedent = t

    return prix
```

**Traduction en phrase :** Pour chaque date, je calcule le temps écoulé depuis la précédente, tire un choc par scénario, calcule les nouveaux prix et avance ma date de référence. Je renvoie ensuite le tableau entier.

Pour `[0.25, 0.75, 1.0]`, les durées sont `0.25`, `0.50`, `0.25`. Le code accepte donc des espacements irréguliers. Dans `normal(0, 1, n_simulations)`, 0 est la moyenne et 1 l’écart-type, pas la variance.

**Si on change le code :** retirer `t_precedent = t` ferait utiliser les durées depuis aujourd’hui à chaque étape, en les cumulant à tort. Remplacer `sqrt(dt)` par `dt` donnerait une mauvaise amplitude des chocs. Augmenter le nombre de scénarios réduit généralement le bruit mais consomme davantage de mémoire.

<a id="phoenix"></a>
## 6. Phoenix, bloc par bloc

### 6.1 Signature : les options du Phoenix

**Lignes 85–87 de `strutu_engine_pedagogique.py`**

```python
def price_phoenix(S0, r, q, sigma, obs_dates, K_auto, B_phoenix, B_pdi, coupon,
                   n_simulations, memory=True, has_autocall=True,
                   bonus_threshold=None, bonus_amount=0.0, strike_pct=1.0):
```

**Traduction en phrase :** Je définis un Phoenix dont les mécanismes peuvent être activés par des arguments simples : mémoire, rappel, bonus et strike personnalisé.

Sans précision, la mémoire et le rappel sont activés ; aucun bonus n’est versé. Le step-up n’a pas de bouton spécifique : c’est une liste de coupons. `memory=False` change la règle de paiement, tandis que `n_simulations` change seulement l’effort numérique.

### 6.2 Simulation et niveaux de barrière

**Lignes 103–110 de `strutu_engine_pedagogique.py`**

```python
    n_dates = len(obs_dates)
    prix = simulate_observation_dates(S0, r, q, sigma, obs_dates, n_simulations)

    # Convertir les barrières relatives en prix du sous-jacent.
    strike_reference = strike_pct * S0
    K_auto_level = K_auto * strike_reference
    B_phoenix_level = B_phoenix * strike_reference
    B_pdi_level = B_pdi * strike_reference
```

**Traduction en phrase :** Je simule les prix puis transforme les seuils relatifs du contrat en niveaux de prix comparables aux fixings.

Avec `S0=100`, `strike_pct=0.90`, `K_auto=1`, `B_phoenix=0.80`, `B_pdi=0.60`, les niveaux valent 90, 72 et 54. **Changer le strike change toutes ces barrières, le seuil du bonus et le dénominateur de la perte finale.** Il ne change pas le point de départ simulé, qui reste `S0=100`.

### 6.3 Coupon fixe ou step-up

**Lignes 112–115 de `strutu_engine_pedagogique.py`**

```python
    if np.isscalar(coupon):
        coupon_schedule = np.full(n_dates, coupon)
    else:
        coupon_schedule = np.asarray(coupon)
```

**Traduction en phrase :** Si le coupon est un nombre, je le répète pour toutes les dates. Sinon, je prends la liste de coupons fournie.

Pour trois dates, `0.02` devient `[0.02, 0.02, 0.02]`. La liste `[0.01, 0.02, 0.03]` représente trois montants différents. Le code n’impose pas qu’ils soient croissants : cette propriété relève des paramètres du contrat. Une liste trop courte provoquera une erreur pendant la boucle ; une liste trop longue laissera ses valeurs excédentaires inutilisées.

### 6.4 Suivre l’état de chaque contrat

**Lignes 119–122 de `strutu_engine_pedagogique.py`**

```python
    flux_actualises = np.zeros(n_simulations)
    rappele = np.zeros(n_simulations, dtype=bool)
    # Chaque scénario possède sa propre réserve de coupons non versés.
    coupons_en_attente = np.zeros(n_simulations)
```

**Traduction en phrase :** Je prépare, pour chaque scénario, une somme de paiements nulle, un indicateur « pas encore rappelé » et un stock de coupons impayés nul.

Trois scénarios donnent trois cases dans chacun des tableaux. Les contrats ne sont pas rappelés aux mêmes dates : un seul booléen pour tout le calcul ne suffirait pas. `dtype=bool` rend `~rappele` utilisable comme inversion logique.

### 6.5 Lire le fixing et actualiser

**Lignes 124–129 de `strutu_engine_pedagogique.py`**

```python
    for k in range(1, n_dates + 1):
        t_k = obs_dates[k-1]
        S_k = prix[:, k]
        actualisation = np.exp(-r * t_k)

        actifs = ~rappele
```

**Traduction en phrase :** À chaque observation, je récupère sa date et ses prix, calcule le facteur d’actualisation et identifie les contrats encore vivants.

`k=1` correspond à `obs_dates[0]` et à `prix[:, 1]`. Le masque `actifs` empêche de payer à nouveau un contrat déjà remboursé. Retirer ce filtre peut créer des coupons après la fin du contrat et surévaluer le produit.

### 6.6 Conditions de rappel et de coupon

**Lignes 138–143 de `strutu_engine_pedagogique.py`**

```python
        if has_autocall and k < n_dates:
            autocall_now = actifs & (S_k >= K_auto_level)
        else:
            autocall_now = np.zeros(n_simulations, dtype=bool)

        coupon_du = actifs & (S_k >= B_phoenix_level)
```

**Traduction en phrase :** Je teste le rappel uniquement s’il est activé et si nous sommes avant la dernière observation. Je teste séparément si le coupon est dû.

L’égalité suffit : un spot de 100 franchit une barrière de 100 avec `>=`. Remplacer ce signe par `>` changerait le cas d’égalité. Le coupon n’est pas automatiquement dû lors d’un rappel : si les paramètres placent la barrière coupon au-dessus du niveau atteint, le capital peut être remboursé sans coupon.

`k < n_dates` permet au contrat arrivant normalement à maturité de rester éligible au bonus final. Remplacer `<` par `<=` changerait ce comportement.

### 6.7 Mémoire : ajouter, payer, remettre à zéro

**Lignes 145–154 de `strutu_engine_pedagogique.py`**

```python
        coupon_periode = coupon_schedule[k-1]
        if memory:
            # Ajouter le coupon courant aux coupons précédemment manqués.
            coupons_en_attente += np.where(actifs, coupon_periode, 0.0)
            montant_coupon = np.where(coupon_du, coupons_en_attente, 0.0)
            # Une fois payé, le stock de coupons revient à zéro.
            coupons_en_attente = np.where(coupon_du, 0.0, coupons_en_attente)
        else:
            # Sans mémoire, un coupon manqué est définitivement perdu.
            montant_coupon = np.where(coupon_du, coupon_periode, 0.0)
```

**Traduction en phrase :** Avec mémoire, j’ajoute le coupon courant au stock impayé, verse le stock si la condition coupon est satisfaite, puis vide ce stock. Sans mémoire, je verse seulement le coupon courant lorsqu’il est dû.

Exemple : coupons de 2 %, 3 %, 4 % ; les deux premières observations échouent et la troisième réussit. Avec mémoire : stock de 2 %, puis 5 %, puis paiement de 9 %. Sans mémoire : seul 4 % est versé.

**Pourquoi cet ordre ?** Il faut ajouter avant de payer pour inclure le coupon du jour, puis remettre à zéro après avoir déterminé le paiement. Oublier la remise à zéro ferait repayer les anciens coupons. Les coupons encore impayés à la fin ne sont pas automatiquement récupérés : un fixing éligible reste nécessaire.

### 6.8 Verser et fermer les contrats rappelés

**Lignes 157–161 de `strutu_engine_pedagogique.py`**

```python
        flux_actualises += montant_coupon * actualisation
        # Le rappel rend également le capital de 1 à l'investisseur.
        flux_actualises += np.where(autocall_now, 1.0 * actualisation, 0.0)

        rappele = rappele | autocall_now
```

**Traduction en phrase :** J’ajoute le coupon actualisé et, pour les scénarios rappelés aujourd’hui, le capital actualisé. Je conserve ensuite la trace de tous les rappels passés et présents.

À six mois, avec un coupon de 2 % et un rappel, le flux ajouté vaut `1.02 * exp(-r * 0.5)`. Le coupon est déjà nul pour les scénarios inéligibles. `rappele | autocall_now` garde les anciens `True`. Écrire seulement `rappele = autocall_now` pourrait réactiver des contrats terminés.

### 6.9 Capital à maturité

**Lignes 163–169 de `strutu_engine_pedagogique.py`**

```python
    S_T = prix[:, n_dates]
    actualisation_T = np.exp(-r * obs_dates[-1])
    non_rappelees = ~rappele

    # Protection observée uniquement à maturité : égalité = capital protégé.
    # Sous la barrière, le capital suit le ratio prix final / strike.
    remboursement_T = np.where(S_T >= B_pdi_level, 1.0, S_T / strike_reference)
```

**Traduction en phrase :** Je prends les prix finaux, actualise à la dernière date et calcule le capital selon la protection à maturité.

Le masque `non_rappelees` servira à réserver ce capital aux contrats encore en vie. Avec strike 100, barrière 60 et spot final 60, le capital vaut 1 ; avec spot final 59, il vaut 0.59. Cette discontinuité vient du contrat codé. Ce remboursement n’inclut pas le coupon final, traité dans la boucle.

### 6.10 Bonus, dernier versement et moyenne

**Lignes 171–178 de `strutu_engine_pedagogique.py`**

```python
    if bonus_threshold is not None:
        bonus_du = non_rappelees & (S_T >= bonus_threshold * strike_reference)
        remboursement_T = remboursement_T + np.where(bonus_du, bonus_amount, 0.0)

    flux_actualises += np.where(non_rappelees, remboursement_T * actualisation_T, 0.0)

    # Le prix Monte-Carlo est la moyenne des paiements actualisés.
    return np.mean(flux_actualises)
```

**Traduction en phrase :** Si un seuil de bonus est fourni, j’ajoute le bonus aux contrats non rappelés qui le franchissent. Je verse ensuite le remboursement final actualisé aux survivants et renvoie la moyenne de tous les scénarios.

Avec un strike de 100, un seuil de 1 et un bonus de 5 %, un prix final de 105 ajoute 0.05 au capital. Le bonus ne remplace pas le coupon. Un contrat rappelé plus tôt ne le reçoit pas. Le code teste le seuil du bonus indépendamment de la barrière PDI : choisir des seuils inhabituels peut donc cumuler bonus et capital réduit.

Remplacer `np.mean` par `np.sum` multiplierait le prix par le nombre de scénarios. Le résultat est un prix, pas la performance réalisée d’un investissement.

### 6.11 Un Phoenix suivi à la main

Prenons trois observations, strike 100, barrière coupon 80, rappel 100, PDI 60, coupon 2 %, mémoire activée, taux nul et trajectoire **100 → 70 → 90 → 105**.

| Observation | Prix | Coupon payé | Stock après paiement | Capital payé |
|---|---:|---:|---:|---:|
| 1 | 70 | 0 | 0.02 | 0 |
| 2 | 90 | 0.04 | 0 | 0 |
| 3, maturité | 105 | 0.02 | 0 | 1 |

Total : **1.06**. Avec un bonus de 5 % au seuil de 100, total : **1.11**. Sans mémoire et sans bonus : **1.04**. Si le prix de la deuxième observation avait été 105, le produit aurait été rappelé à cette date et la troisième observation n’aurait donné aucun paiement.

<a id="zenith"></a>
## 7. Zenith, bloc par bloc

### 7.1 Définir et préparer les paliers

**Lignes 185–206 de `strutu_engine_pedagogique.py`**

```python
def price_zenith(S0, r, q, sigma, obs_dates, K_levels, C_levels, B_pdi,
                  n_simulations, strike_pct=1.0):
    """
    Prix d'un Zenith par Monte Carlo : plusieurs barrières emboîtées K1 < K2 < ... < Kn,
    chacune associée à un coupon C1 < C2 < ... < Cn. Seul le palier le plus haut
    franchi déclenche l'autocall (+ le coupon du palier le plus haut) ; les paliers
    intermédiaires ne versent qu'un coupon, sans rappel.

    K_levels, C_levels : listes de même longueur, dans l'ordre croissant.
    """
    assert len(K_levels) == len(C_levels), "K_levels et C_levels doivent avoir la même longueur"

    n_dates = len(obs_dates)
    prix = simulate_observation_dates(S0, r, q, sigma, obs_dates, n_simulations)

    # Convertir les barrières relatives en prix du sous-jacent.
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

### 7.2 Préparer la date et le coupon

**Lignes 209–218 de `strutu_engine_pedagogique.py`**

```python
    flux_actualises = np.zeros(n_simulations)
    rappele = np.zeros(n_simulations, dtype=bool)

    for k in range(1, n_dates + 1):
        t_k = obs_dates[k-1]
        S_k = prix[:, k]
        actualisation = np.exp(-r * t_k)
        actifs = ~rappele

        montant_coupon = np.zeros(n_simulations)
```

**Traduction en phrase :** Je prépare le suivi des contrats puis, à chaque date, je pars d’un coupon nul et je regarde les scénarios encore actifs.

Le coupon est remis à zéro **dans** la boucle des dates. Sinon, un coupon d’une ancienne observation pourrait rester présent alors qu’aucun palier n’est franchi aujourd’hui. Zenith n’utilise pas de stock de coupons impayés.

### 7.3 Garder le coupon du meilleur palier

**Lignes 221–231 de `strutu_engine_pedagogique.py`**

```python
        for i in range(n_paliers):
            franchi = actifs & (S_k >= K_levels_abs[i])
            montant_coupon = np.where(franchi, C_levels[i], montant_coupon)

        # Convention d’origine Zenith : test du rappel aussi à la dernière date.
        # Seul le dernier palier (le plus élevé) rembourse aussi le capital.
        autocall_now = actifs & (S_k >= K_levels_abs[-1])
        flux_actualises += montant_coupon * actualisation
        flux_actualises += np.where(autocall_now, 1.0 * actualisation, 0.0)

        rappele = rappele | autocall_now
```

**Traduction en phrase :** Je parcours les paliers croissants. Chaque palier franchi remplace le coupon précédent. Le dernier palier déclenche également le remboursement du capital.

Avec des seuils 80, 100, 110 et des coupons 1 %, 2 %, 4 % : spot 95 → 1 % sans rappel ; spot 105 → 2 % sans rappel ; spot 115 → 4 % plus le capital. On ne verse pas `1 % + 2 % + 4 %`.

`K_levels_abs[-1]` est le dernier seuil. Ce n’est le plus élevé que si la liste est ordonnée. Remplacer l’affectation du coupon par une addition transformerait le produit en coupons cumulés. Dans ce fichier, le test de rappel existe aussi à la dernière observation.

### 7.4 Remboursement final du Zenith

**Lignes 233–243 de `strutu_engine_pedagogique.py`**

```python
    S_T = prix[:, n_dates]
    actualisation_T = np.exp(-r * obs_dates[-1])
    non_rappelees = ~rappele

    # Protection observée uniquement à maturité : égalité = capital protégé.
    # Sous la barrière, le capital suit le ratio prix final / strike.
    remboursement_T = np.where(S_T >= B_pdi_level, 1.0, S_T / strike_reference)
    flux_actualises += np.where(non_rappelees, remboursement_T * actualisation_T, 0.0)

    # Le prix Monte-Carlo est la moyenne des paiements actualisés.
    return np.mean(flux_actualises)
```

**Traduction en phrase :** Pour les contrats qui n’ont pas franchi le dernier palier, je règle le capital à maturité selon la PDI, puis je moyenne les paiements actualisés.

Un contrat traité comme rappelé à la dernière observation a déjà reçu son capital dans la boucle : le masque évite un deuxième versement. Avec spot final 50, strike 100 et PDI 60, un survivant reçoit 0.50 de capital. Les coupons déjà versés restent acquis.

<a id="dm"></a>
## 8. Double Memory, bloc par bloc

### 8.1 Deux mémoires de nature différente

**Lignes 250–252 de `strutu_engine_pedagogique.py`**

```python
def price_phoenix_dm(S0, r, q, sigma, obs_dates, K_auto, B_phoenix, B_pdi, coupon,
                      n_simulations, dm_version="A", dm_window=3, dm_stat="mean",
                      K_auto_memory=None, memory=True, strike_pct=1.0):
```

**Traduction en phrase :** Je définis un Phoenix avec une mémoire de prix sur plusieurs observations et, si `memory=True`, une mémoire des coupons impayés.

`dm_version="A"` ajoute une condition de rappel fondée sur les prix récents. `"B"` remplace le fixing utilisé pour le coupon par une statistique des prix récents. `dm_window=3` signifie trois observations, pas trois années. `dm_stat="mean"` prend leur moyenne ; `"max"` leur maximum.

### 8.2 Choisir le seuil de rappel avec mémoire

**Lignes 274–285 de `strutu_engine_pedagogique.py`**

```python
    n_dates = len(obs_dates)
    prix = simulate_observation_dates(S0, r, q, sigma, obs_dates, n_simulations)

    # Convertir les barrières relatives en prix du sous-jacent.
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

### 8.3 Préparer coupons et état des contrats

**Lignes 287–302 de `strutu_engine_pedagogique.py`**

```python
    if np.isscalar(coupon):
        coupon_schedule = np.full(n_dates, coupon)
    else:
        coupon_schedule = np.asarray(coupon)

    # Somme des paiements ramenés à aujourd’hui, pour chaque scénario.
    flux_actualises = np.zeros(n_simulations)
    rappele = np.zeros(n_simulations, dtype=bool)
    # Chaque scénario possède sa propre réserve de coupons non versés.
    coupons_en_attente = np.zeros(n_simulations)

    for k in range(1, n_dates + 1):
        t_k = obs_dates[k-1]
        S_k = prix[:, k]
        actualisation = np.exp(-r * t_k)
        actifs = ~rappele
```

**Traduction en phrase :** Je prépare le calendrier des coupons, les paiements, les rappels et les coupons en attente. À chaque date, je récupère le fixing et les contrats encore vivants.

Ces lignes reprennent les mêmes mécanismes que Phoenix. Le coupon peut être fixe ou une liste ; le stock de coupons est distinct du tableau des prix. Modifier la taille de la fenêtre ne modifie pas directement les montants contractuels des coupons.

### 8.4 Construire la fenêtre de prix

**Lignes 306–311 de `strutu_engine_pedagogique.py`**

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

### 8.5 Appliquer la version A ou B

**Lignes 314–319 de `strutu_engine_pedagogique.py`**

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

### 8.6 Mémoire des coupons et versements

**Lignes 321–337 de `strutu_engine_pedagogique.py`**

```python
        coupon_periode = coupon_schedule[k-1]
        if memory:
            # Ajouter le coupon courant aux coupons précédemment manqués.
            coupons_en_attente += np.where(actifs, coupon_periode, 0.0)
            montant_coupon = np.where(coupon_du, coupons_en_attente, 0.0)
            # Une fois payé, le stock de coupons revient à zéro.
            coupons_en_attente = np.where(coupon_du, 0.0, coupons_en_attente)
        else:
            # Sans mémoire, un coupon manqué est définitivement perdu.
            montant_coupon = np.where(coupon_du, coupon_periode, 0.0)

        # Verser le coupon éligible, y compris en cas de rappel ce jour-là.
        flux_actualises += montant_coupon * actualisation
        # Le rappel rend également le capital de 1 à l'investisseur.
        flux_actualises += np.where(autocall_now, 1.0 * actualisation, 0.0)

        rappele = rappele | autocall_now
```

**Traduction en phrase :** Une fois l’éligibilité décidée, je calcule les coupons à verser, vide la mémoire payée, ajoute les paiements actualisés et ferme les contrats rappelés.

La mémoire monétaire fonctionne comme dans Phoenix : coupons successifs de 1 % puis 3 %, premier paiement refusé et second accepté → 4 % avec mémoire, 3 % sans mémoire. `memory=False` désactive ce rattrapage, mais **ne désactive pas la fenêtre de prix** du Double Memory.

### 8.7 Capital final et prix du DM

**Lignes 339–348 de `strutu_engine_pedagogique.py`**

```python
    S_T = prix[:, n_dates]
    actualisation_T = np.exp(-r * obs_dates[-1])
    non_rappelees = ~rappele
    # Protection observée uniquement à maturité : égalité = capital protégé.
    # Sous la barrière, le capital suit le ratio prix final / strike.
    remboursement_T = np.where(S_T >= B_pdi_level, 1.0, S_T / strike_reference)
    flux_actualises += np.where(non_rappelees, remboursement_T * actualisation_T, 0.0)

    # Le prix Monte-Carlo est la moyenne des paiements actualisés.
    return np.mean(flux_actualises)
```

**Traduction en phrase :** Je rembourse les survivants selon le prix final et la barrière PDI, puis calcule leur contribution au prix moyen.

La statistique de fenêtre ne remplace pas `S_T` pour la protection finale. Un prix final inférieur à la PDI peut donc entraîner une perte même si la moyenne récente est meilleure, tant que le contrat n’a pas été rappelé. Il n’y a pas d’argument de bonus dans cette fonction.

<a id="japan"></a>
## 9. Japan 2, bloc par bloc

### 9.1 Paramètres particuliers

**Lignes 355–357 de `strutu_engine_pedagogique.py`**

```python
def price_phoenix_japan2(S0, r, q, sigma, T, obs_dates,
                          K_auto, B_coupon_low, B_pdi, coupon,
                          n_simulations, strike_pct=1.0, trading_days_per_year=252):
```

**Traduction en phrase :** Je définis un produit avec une maturité explicite, une grille journalière, des coupons proportionnels aux jours éligibles et une barrière de protection surveillée pendant la vie du contrat.

`T` définit la fin de simulation. `obs_dates` définit les dates de versement et de rappel. `trading_days_per_year=252` fixe une densité de grille ; il ne charge pas un calendrier réel de jours fériés. Le coupon est ici un montant scalaire maximal par période.

### 9.2 Simuler chaque jour de la grille

**Lignes 378–385 de `strutu_engine_pedagogique.py`**

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

### 9.3 Niveaux et suivi de la PDI

**Lignes 388–397 de `strutu_engine_pedagogique.py`**

```python
    strike_reference = strike_pct * S0
    K_auto_level = K_auto * strike_reference
    B_coupon_level = B_coupon_low * strike_reference
    B_pdi_level = B_pdi * strike_reference

    # PDI américaine : franchie si le spot est passé sous la barrière n'importe quel jour.
    # Inclut S0 ; égalité = barrière touchée. Observation sur la grille,
    # pas en temps continu entre deux jours. Le test sur toute la trajectoire
    # est sans effet pour les contrats rappelés : leur capital est déjà versé.
    pdi_touchee = (prix <= B_pdi_level).any(axis=1)
```

**Traduction en phrase :** Je calcule les niveaux de prix, puis je demande pour chaque trajectoire si le sous-jacent a atteint ou traversé la barrière PDI au moins une fois.

Pour une barrière de 60, la trajectoire `[100, 58, 105]` active la PDI malgré son rebond. L’égalité active aussi la barrière à cause de `<=`. Le tableau comprend `S0`, donc un départ sur la barrière l’active immédiatement.

`.any(axis=1)` ne compte pas les jours : un seul suffit. La surveillance est journalière sur la grille, pas continue entre deux points. Tester toute la trajectoire à l’avance ne décide pas le rappel avec une information future : ce résultat sert uniquement au capital final des contrats non rappelés.

### 9.4 Convertir les observations en jours

**Lignes 400–406 de `strutu_engine_pedagogique.py`**

```python
    flux_actualises = np.zeros(n_simulations)
    rappele = np.zeros(n_simulations, dtype=bool)

    obs_days = []
    for t in obs_dates:
        jour_observation = int(round(t / dt))
        obs_days.append(jour_observation)
```

**Traduction en phrase :** Je prépare les paiements et les rappels, puis transforme chaque date d’observation en position sur la grille journalière.

Avec `dt=1/252`, la date `0.25` donne le jour 63. Les dates sont arrondies, mais l’actualisation restera calculée à la date contractuelle. Deux dates très proches peuvent tomber sur le même jour : la seconde période aurait alors zéro jour, ce que le code ne protège pas.

### 9.5 Délimiter chaque période

**Lignes 408–413 de `strutu_engine_pedagogique.py`**

```python
    jour_debut_periode = 0
    for k in range(len(obs_days)):
        jour_fin = obs_days[k]
        t_k = obs_dates[k]
        actualisation = np.exp(-r * t_k)
        actifs = ~rappele
```

**Traduction en phrase :** Je commence après aujourd’hui et, pour chaque observation, récupère son jour de fin, sa date contractuelle et les contrats encore actifs.

Ici `k` commence à 0 : `obs_days[k]` et `obs_dates[k]` ont les mêmes positions. Le fixing sera lu avec `jour_fin`, pas avec `k`. Confondre ces indices sélectionnerait un des tout premiers jours au lieu de la date d’observation.

### 9.6 Calculer le coupon proportionnel

**Lignes 415–420 de `strutu_engine_pedagogique.py`**

```python
        periode = prix[:, jour_debut_periode+1:jour_fin+1]
        n_jours_periode = periode.shape[1]
        jours_au_dessus = (periode >= B_coupon_level).sum(axis=1)
        # Exemple : 15 jours éligibles sur 20 donnent 75 % du coupon plein.
        fraction = jours_au_dessus / n_jours_periode
        montant_coupon = fraction * coupon
```

**Traduction en phrase :** Je prends les jours de la période, compte ceux où la condition de coupon est satisfaite et verse la fraction correspondante du coupon plein.

Une première période finissant au jour 63 prend les jours 1 à 63 ; la suivante commence au jour 64. La borne initiale exclut le fixing déjà compté dans la période précédente. La borne finale inclut le jour d’observation.

Sur 20 jours, 15 jours éligibles et un coupon plein de 4 % donnent `15/20 × 0.04 = 0.03`, soit 3 %. `shape[1]` fournit les 20 jours ; `shape[0]` donnerait le nombre de scénarios et serait faux. Les coupons sont payés en fin de période : ils ne sont pas actualisés jour par jour.

### 9.7 Coupon acquis et remboursement au rappel

**Lignes 422–431 de `strutu_engine_pedagogique.py`**

```python
        S_k = prix[:, jour_fin]
        # Convention d’origine Japan 2 : test du rappel aussi à la dernière date.
        autocall_now = actifs & (S_k >= K_auto_level)

        # Tous les contrats encore actifs touchent le coupon journalier acquis.
        flux_actualises += np.where(actifs, montant_coupon * actualisation, 0.0)
        flux_actualises += np.where(autocall_now, 1.0 * actualisation, 0.0)

        rappele = rappele | autocall_now
        jour_debut_periode = jour_fin
```

**Traduction en phrase :** Je regarde le fixing de fin de période, verse le coupon acquis aux contrats actifs, rembourse ceux rappelés et prépare le début de la période suivante.

Le rappel est testé aux dates de `obs_dates`, pas tous les jours. Une hausse au-dessus de la barrière entre deux observations ne suffit pas. Le coupon dépend des jours de la période ; le rappel dépend du fixing de fin. Comme dans Zenith et DM, le test est effectué aussi à la dernière observation.

Oublier `jour_debut_periode = jour_fin` ferait recompter les jours depuis aujourd’hui à chaque coupon.

### 9.8 Capital après une barrière touchée

**Lignes 433–446 de `strutu_engine_pedagogique.py`**

```python
    non_rappelees = ~rappele
    S_T = prix[:, n_days]
    actualisation_T = np.exp(-r * T)

    # Une fois la PDI touchée, le capital est exposé à la baisse du sous-jacent
    # (S_T/strike), mais ça reste une protection dégradée, pas une participation
    # à la hausse : le remboursement ne doit jamais dépasser 100% même si le
    # sous-jacent a fini par remonter au-dessus du strike après avoir franchi
    # la barrière en cours de vie.
    remboursement_T = np.where(pdi_touchee & non_rappelees, np.minimum(S_T / strike_reference, 1.0), 1.0)
    flux_actualises += np.where(non_rappelees, remboursement_T * actualisation_T, 0.0)

    # Le prix Monte-Carlo est la moyenne des paiements actualisés.
    return np.mean(flux_actualises)
```

**Traduction en phrase :** Pour les contrats non rappelés, je rembourse 1 si la PDI n’a jamais été touchée. Si elle l’a été, je verse le ratio du prix final au strike, plafonné à 1. J’actualise ce capital à T et renvoie le prix moyen.

Avec strike 100 et PDI touchée : prix final 50 → capital 0.50 ; prix final 90 → 0.90 ; prix final 110 → 1.00 grâce au plafond. Sans PDI touchée, le capital reste 1. Les coupons déjà acquis s’ajoutent à ces montants.

Retirer `np.minimum(..., 1.0)` autoriserait un capital supérieur à 100 % après un rebond. Si la dernière observation est avant T, le code paie le capital à T mais ne crée pas automatiquement un coupon pour la période restante.

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

