import numpy as np


# =========================
# Simulation aux dates d'observation
# =========================

def simulate_observation_dates(S0, r, q, sigma, obs_dates, n_simulations):
    """
    Simule le prix du sous-jacent à chaque date d'observation.

    obs_dates : liste des dates d'observation en années, ex: [0.25, 0.5, 0.75, 1.0]
    Renvoie un tableau numpy de forme (n_simulations, len(obs_dates) + 1) :
    colonne 0 = S0, colonne i = prix à obs_dates[i-1].
    """
    n_dates = len(obs_dates)
    prix = np.zeros((n_simulations, n_dates + 1))
    prix[:, 0] = S0

    t_precedent = 0
    for i, t in enumerate(obs_dates):
        dt = t - t_precedent
        Z = np.random.normal(0, 1, n_simulations)
        prix[:, i+1] = prix[:, i] * np.exp(
            (r - q - sigma**2 / 2) * dt + sigma * np.sqrt(dt) * Z
        )
        t_precedent = t

    return prix


# =========================
# Phoenix générique (standard / memory / bonus / step-up / sans autocall / Custom Strike)
# =========================

def price_phoenix(S0, r, q, sigma, obs_dates, K_auto, B_phoenix, B_pdi, coupon,
                   n_simulations, memory=True, has_autocall=True,
                   bonus_threshold=None, bonus_amount=0.0, strike_pct=1.0):
    """
    Prix d'un Phoenix générique par Monte Carlo, couvrant :
    - Phoenix coupon standard   : memory=False
    - Phoenix memory            : memory=True
    - Phoenix bonus à maturité  : bonus_threshold + bonus_amount
    - Phoenix coupon-only autocall : memory=False, has_autocall=True
    - Phoenix sans autocall     : has_autocall=False
    - Phoenix step-up coupon    : coupon = liste/array croissante au lieu d'un nombre
    - Phoenix Custom Strike     : strike_pct != 1.0 (toutes les barrières sont
      recalculées en % de custom_strike = strike_pct * S0, pas de S0 directement)

    K_auto, B_phoenix, B_pdi : niveaux en % du strike de référence.
    coupon : un nombre (coupon fixe chaque période) ou un tableau de longueur
             len(obs_dates) (step-up).
    """
    n_dates = len(obs_dates)
    prix = simulate_observation_dates(S0, r, q, sigma, obs_dates, n_simulations)

    custom_strike = strike_pct * S0
    K_auto_level = K_auto * custom_strike
    B_phoenix_level = B_phoenix * custom_strike
    B_pdi_level = B_pdi * custom_strike

    if np.isscalar(coupon):
        coupon_schedule = np.full(n_dates, coupon)
    else:
        coupon_schedule = np.asarray(coupon)

    cum_coupon = np.concatenate(([0.0], np.cumsum(coupon_schedule)))

    cashflow = np.zeros(n_simulations)
    called = np.zeros(n_simulations, dtype=bool)
    last_coupon_date = np.zeros(n_simulations, dtype=int)

    for k in range(1, n_dates + 1):
        t_k = obs_dates[k-1]
        S_k = prix[:, k]
        discount = np.exp(-r * t_k)

        actifs = ~called

        # L'autocall ne s'applique qu'aux observations STRICTEMENT avant
        # l'échéance. À la toute dernière date, franchir le callable level
        # ne constitue pas un "rappel anticipé" — c'est simplement le
        # règlement normal à maturité (qui doit rester éligible au bonus,
        # au coupon final, etc.). Sans cette distinction, un produit qui
        # finit sa vie normalement au-dessus du callable level était traité
        # à tort comme rappelé, et perdait injustement son bonus.
        if has_autocall and k < n_dates:
            autocall_now = actifs & (S_k >= K_auto_level)
        else:
            autocall_now = np.zeros(n_simulations, dtype=bool)

        coupon_du = actifs & (S_k >= B_phoenix_level)

        if memory:
            montant_si_du = cum_coupon[k] - cum_coupon[last_coupon_date]
        else:
            montant_si_du = coupon_schedule[k-1]

        montant_coupon = np.where(coupon_du, montant_si_du, 0.0)

        cashflow += np.where(autocall_now, (1.0 + montant_coupon) * discount, 0.0)
        cashflow += np.where(actifs & ~autocall_now & coupon_du, montant_coupon * discount, 0.0)

        last_coupon_date = np.where(actifs & coupon_du, k, last_coupon_date)
        called = called | autocall_now

    S_T = prix[:, n_dates]
    discount_T = np.exp(-r * obs_dates[-1])
    non_rappelees = ~called

    remboursement_T = np.where(S_T >= B_pdi_level, 1.0, S_T / custom_strike)

    if bonus_threshold is not None:
        bonus_du = non_rappelees & (S_T >= bonus_threshold * custom_strike)
        remboursement_T = remboursement_T + np.where(bonus_du, bonus_amount, 0.0)

    cashflow += np.where(non_rappelees, remboursement_T * discount_T, 0.0)

    return np.mean(cashflow)


# =========================
# Zenith (barrières et coupons étagés)
# =========================

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

    custom_strike = strike_pct * S0
    K_levels_abs = [k * custom_strike for k in K_levels]
    B_pdi_level = B_pdi * custom_strike
    n_paliers = len(K_levels_abs)

    cashflow = np.zeros(n_simulations)
    called = np.zeros(n_simulations, dtype=bool)

    for k in range(1, n_dates + 1):
        t_k = obs_dates[k-1]
        S_k = prix[:, k]
        discount = np.exp(-r * t_k)
        actifs = ~called

        montant_coupon = np.zeros(n_simulations)
        palier_du = np.zeros(n_simulations, dtype=bool)
        autocall_now = np.zeros(n_simulations, dtype=bool)

        # On part du palier le plus haut et on redescend : le premier palier
        # franchi (en partant du haut) est celui qui s'applique à cette trajectoire.
        for i in range(n_paliers - 1, -1, -1):
            franchi = actifs & ~palier_du & (S_k >= K_levels_abs[i])
            montant_coupon = np.where(franchi, C_levels[i], montant_coupon)
            palier_du = palier_du | franchi
            if i == n_paliers - 1:
                autocall_now = franchi  # seul le palier le plus haut déclenche le rappel

        cashflow += np.where(autocall_now, (1.0 + montant_coupon) * discount, 0.0)
        cashflow += np.where(actifs & ~autocall_now & palier_du, montant_coupon * discount, 0.0)

        called = called | autocall_now

    S_T = prix[:, n_dates]
    discount_T = np.exp(-r * obs_dates[-1])
    non_rappelees = ~called

    remboursement_T = np.where(S_T >= B_pdi_level, 1.0, S_T / custom_strike)
    cashflow += np.where(non_rappelees, remboursement_T * discount_T, 0.0)

    return np.mean(cashflow)


# =========================
# Phoenix DM (Double Memory)
# =========================

def price_phoenix_dm(S0, r, q, sigma, obs_dates, K_auto, B_phoenix, B_pdi, coupon,
                      n_simulations, dm_version="A", dm_window=3, dm_stat="mean",
                      K_auto_memory=None, memory=True, strike_pct=1.0):
    """
    Prix d'un Phoenix DM par Monte Carlo.

    dm_version "A" : mémoire sur l'autocall — le produit est aussi rappelé si la
        moyenne (ou le max, selon dm_stat) des `dm_window` dernières observations
        dépasse K_auto_memory, un seuil DISTINCT et plus bas que K_auto (sinon
        cette condition ne peut mathématiquement jamais se déclencher en plus de
        la condition ponctuelle : la moyenne de plusieurs points ne dépasse jamais
        leur maximum, donc si la moyenne franchit K_auto, un point l'aurait déjà
        franchi individuellement à une date antérieure). Si K_auto_memory n'est
        pas fourni, on prend K_auto par défaut, ce qui revient alors à désactiver
        la mémoire (comportement identique à un Phoenix standard) — à toi de
        fixer un niveau plus bas pour que la fonctionnalité soit active.
    dm_version "B" : mémoire sur la barrière coupon — le coupon est décidé sur la
        moyenne (ou le max) des `dm_window` dernières observations plutôt que sur
        le seul fixing du jour. Ce cas-ci reste valide avec le même seuil
        B_phoenix, car il ne s'agit pas d'une condition "OU" avec le point actuel,
        mais d'un remplacement : on ne regarde plus jamais le point seul.
    dm_window : nombre d'observations récentes prises en compte.
    dm_stat   : "mean" ou "max".
    """
    n_dates = len(obs_dates)
    prix = simulate_observation_dates(S0, r, q, sigma, obs_dates, n_simulations)

    custom_strike = strike_pct * S0
    K_auto_level = K_auto * custom_strike
    K_auto_memory_level = (K_auto_memory if K_auto_memory is not None else K_auto) * custom_strike
    B_phoenix_level = B_phoenix * custom_strike
    B_pdi_level = B_pdi * custom_strike

    if np.isscalar(coupon):
        coupon_schedule = np.full(n_dates, coupon)
    else:
        coupon_schedule = np.asarray(coupon)
    cum_coupon = np.concatenate(([0.0], np.cumsum(coupon_schedule)))

    cashflow = np.zeros(n_simulations)
    called = np.zeros(n_simulations, dtype=bool)
    last_coupon_date = np.zeros(n_simulations, dtype=int)

    def stat_fenetre(k):
        """Moyenne (ou max) du prix sur les `dm_window` dernières dates (1..k incluses)."""
        debut = max(1, k - dm_window + 1)
        fenetre = prix[:, debut:k+1]
        return fenetre.max(axis=1) if dm_stat == "max" else fenetre.mean(axis=1)

    for k in range(1, n_dates + 1):
        t_k = obs_dates[k-1]
        S_k = prix[:, k]
        discount = np.exp(-r * t_k)
        actifs = ~called

        stat_k = stat_fenetre(k)

        if dm_version == "A":
            autocall_now = actifs & ((S_k >= K_auto_level) | (stat_k >= K_auto_memory_level))
            coupon_du = actifs & (S_k >= B_phoenix_level)
        else:
            autocall_now = actifs & (S_k >= K_auto_level)
            coupon_du = actifs & (stat_k >= B_phoenix_level)

        if memory:
            montant_si_du = cum_coupon[k] - cum_coupon[last_coupon_date]
        else:
            montant_si_du = coupon_schedule[k-1]

        montant_coupon = np.where(coupon_du, montant_si_du, 0.0)

        cashflow += np.where(autocall_now, (1.0 + montant_coupon) * discount, 0.0)
        cashflow += np.where(actifs & ~autocall_now & coupon_du, montant_coupon * discount, 0.0)

        last_coupon_date = np.where(actifs & coupon_du, k, last_coupon_date)
        called = called | autocall_now

    S_T = prix[:, n_dates]
    discount_T = np.exp(-r * obs_dates[-1])
    non_rappelees = ~called
    remboursement_T = np.where(S_T >= B_pdi_level, 1.0, S_T / custom_strike)
    cashflow += np.where(non_rappelees, remboursement_T * discount_T, 0.0)

    return np.mean(cashflow)


# =========================
# Phoenix Japan 2 (coupon journalier + PDI américaine)
# =========================

def price_phoenix_japan2(S0, r, q, sigma, T, obs_dates,
                          K_auto, B_coupon_low, B_pdi, coupon,
                          n_simulations, strike_pct=1.0, trading_days_per_year=252):
    """
    Prix d'un Phoenix Japan 2 par Monte Carlo à fréquence journalière.

    obs_dates       : dates d'observation de l'autocall (en années), comme price_phoenix.
                      Les périodes de coupon sont délimitées directement par ces dates
                      (traduites en indices de jours sur la grille journalière) — aucun
                      paramètre séparé de "jours par période" n'est nécessaire, la grille
                      journalière donne déjà le nombre exact de jours dans chaque période.
    B_coupon_low    : barrière de coupon basse, observée quotidiennement, en % du strike.
    B_pdi           : barrière PDI américaine — franchie une seule fois = activée
                      définitivement pour le reste de la vie du produit.
    coupon          : coupon maximal (plein) par période ; versé en proportion n/N des
                      jours où le sous-jacent est au-dessus de B_coupon_low.

    Hypothèse : grille journalière régulière sur toute la durée T (trading_days_per_year
    jours par an) ; les dates d'obs_dates sont arrondies au jour le plus proche de cette
    grille pour déterminer les dates d'autocall.
    """
    n_days = int(round(T * trading_days_per_year))
    dt = T / n_days

    prix = np.zeros((n_simulations, n_days + 1))
    prix[:, 0] = S0
    for i in range(1, n_days + 1):
        Z = np.random.normal(0, 1, n_simulations)
        prix[:, i] = prix[:, i-1] * np.exp((r - q - sigma**2/2)*dt + sigma*np.sqrt(dt)*Z)

    custom_strike = strike_pct * S0
    K_auto_level = K_auto * custom_strike
    B_coupon_level = B_coupon_low * custom_strike
    B_pdi_level = B_pdi * custom_strike

    # PDI américaine : franchie si le spot est passé sous la barrière n'importe quel jour.
    pdi_touchee = (prix <= B_pdi_level).any(axis=1)

    cashflow = np.zeros(n_simulations)
    called = np.zeros(n_simulations, dtype=bool)

    obs_days = [int(round(t / dt)) for t in obs_dates]

    jour_debut_periode = 0
    for k, jour_fin in enumerate(obs_days, start=1):
        t_k = obs_dates[k-1]
        discount = np.exp(-r * t_k)
        actifs = ~called

        periode = prix[:, jour_debut_periode+1:jour_fin+1]
        n_jours_periode = periode.shape[1]
        jours_au_dessus = (periode >= B_coupon_level).sum(axis=1)
        fraction = jours_au_dessus / n_jours_periode
        montant_coupon = fraction * coupon

        S_k = prix[:, jour_fin]
        autocall_now = actifs & (S_k >= K_auto_level)

        cashflow += np.where(autocall_now, (1.0 + montant_coupon) * discount, 0.0)
        cashflow += np.where(actifs & ~autocall_now, montant_coupon * discount, 0.0)

        called = called | autocall_now
        jour_debut_periode = jour_fin

    non_rappelees = ~called
    S_T = prix[:, n_days]
    discount_T = np.exp(-r * T)

    # Une fois la PDI touchée, le capital est exposé à la baisse du sous-jacent
    # (S_T/strike), mais ça reste une protection dégradée, pas une participation
    # à la hausse : le remboursement ne doit jamais dépasser 100% même si le
    # sous-jacent a fini par remonter au-dessus du strike après avoir franchi
    # la barrière en cours de vie.
    remboursement_T = np.where(pdi_touchee & non_rappelees, np.minimum(S_T / custom_strike, 1.0), 1.0)
    cashflow += np.where(non_rappelees, remboursement_T * discount_T, 0.0)

    return np.mean(cashflow)