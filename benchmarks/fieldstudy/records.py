"""Synthetic evidence packets for a retrospective river-monitoring bulletin.

Only the first element returned by make() belongs in a participant workspace.
The literal answer keys are independently calculated from the source ledger.
"""

from textwrap import dedent


def block(text):
    return dedent(text).strip()


# Each row describes a site-period certificate issued by the assay laboratory.
# The compact syntax keeps the full archival record within a single case.
PACKETS = {
    "dev": (
        "September editorial correction, 2025",
        "Use all listed sites. Reconstruct both rounds using information received "
        "by September 18 inclusive. Use the operating definition of samples with "
        "a determinate result (D): positive plus negative.",
        "K,L,M,N",
        """
        A1,K,1,09/02,09/03,+,12,28,10
        B1,L,1,09/02,09/04,+,5,15,5
        C1,M,1,09/04,09/05,+,7,13,2
        D1,N,1,09/08,09/08,+,9,11,3
        A2,K,1,09/10,09/12,+,9,31,10
        D2,N,1,09/09,09/19,-,,,
        C2,M,1,09/13,09/16,-,,,
        E1,K,2,09/12,09/15,+,15,35,0
        F1,L,2,09/13,09/14,+,9,11,8
        G1,M,2,09/14,09/15,+,1,9,1
        H1,N,2,09/15,09/16,+,8,12,6
        F2,L,2,09/16,09/18,+,6,14,1
        H2,N,2,09/17,09/18,-,,,
        H3,N,2,09/18,09/21,+,8,12,0
        """,
        {"sites": "K,L", "first_refs": "A2,B1", "second_refs": "E1,F2",
         "first_pos": 14, "first_den": 60, "second_pos": 21, "second_den": 70,
         "change_pp": 6.67, "relative_change_pct": 28.57},
    ),
    "a": (
        "October yearbook entry, 2025",
        "The editor wants the originally publishable series. Round 1 was sealed "
        "on October 8 and round 2 on October 20; apply each seal independently, "
        "inclusive of that day. Use all listed sites. Use determinate samples (D).",
        "B,C,F,H,S",
        """
        P1,B,1,10/02,10/03,+,6,34,7
        Q1,C,1,10/03,10/04,+,9,11,0
        R1,F,1,10/04,10/04,+,4,6,2
        S1,H,1,10/03,10/05,+,9,21,3
        T1,S,1,10/07,10/09,+,10,10,0
        Q2,C,1,10/06,10/08,+,6,14,3
        P2,B,1,10/05,10/12,+,2,38,7
        R2,F,1,10/06,10/08,-,,,
        R3,F,1,10/08,10/10,+,5,5,2
        U1,B,2,10/11,10/12,+,10,40,5
        V1,C,2,10/12,10/14,+,8,12,1
        W1,F,2,10/12,10/13,+,8,12,0
        X1,H,2,10/13,10/15,+,6,24,0
        Y1,S,2,10/13,10/14,+,15,5,1
        V2,C,2,10/16,10/19,-,,,
        V3,C,2,10/18,10/20,+,5,10,2
        X2,H,2,10/18,10/21,-,,,
        """,
        {"sites": "B,C,H", "first_refs": "P1,Q2,S1", "second_refs": "U1,V3,X1",
         "first_pos": 21, "first_den": 90, "second_pos": 21, "second_den": 95,
         "change_pp": -1.23, "relative_change_pct": -5.26},
    ),
    "b": (
        "March laboratory throughput memo, 2026",
        "Restate both rounds through March 28 inclusive. This memo uses the "
        "operational yield per specimen processed (P): include indeterminates in "
        "the denominator. Sites M and T were method-development controls; exclude "
        "both from production estimates.",
        "D,G,M,R,T,V",
        """
        J1,D,1,03/02,03/03,+,8,12,5
        K1,G,1,03/03,03/03,+,12,18,10
        L1,M,1,03/02,03/05,+,20,10,0
        M1,R,1,03/03,03/04,+,3,7,0
        N1,T,1,03/04,03/06,+,10,10,0
        P1,V,1,03/04,03/06,+,5,5,10
        J2,D,1,03/15,03/19,-,,,
        J3,D,1,03/17,03/21,+,6,14,5
        M2,R,1,03/23,03/28,-,,,
        Q1,D,2,03/11,03/14,+,9,21,0
        R1,G,2,03/15,03/16,+,10,15,5
        S1,M,2,03/13,03/17,+,25,5,5
        T1,R,2,03/12,03/15,+,8,12,0
        U1,T,2,03/13,03/15,+,15,5,3
        V1,V,2,03/14,03/16,+,7,13,0
        R2,G,2,03/19,03/27,+,9,16,10
        V2,V,2,03/22,03/30,-,,,
        """,
        {"sites": "D,G,V", "first_refs": "J3,K1,P1", "second_refs": "Q1,R2,V1",
         "first_pos": 23, "first_den": 85, "second_pos": 25, "second_den": 85,
         "change_pp": 2.35, "relative_change_pct": 8.70},
    ),
    "c": (
        "May sentinel surveillance correction, 2026",
        "Reconstruct both rounds at the May 24 inclusive freeze. Use the "
        "standing sentinel roster as of May 1: A, E, J, W. Extension sites have "
        "since joined the network and appear in the ledger but cannot enter "
        "this longitudinal series. Use determinate samples (D).",
        "A,E,J,Q,W",
        """
        A1,A,1,05/01,05/03,+,12,28,4
        B1,E,1,05/02,05/04,+,4,16,0
        C1,J,1,05/02,05/05,+,9,21,6
        D1,Q,1,05/03,05/04,+,18,12,2
        E1,W,1,05/02,05/04,+,4,6,4
        C2,J,1,05/06,05/10,+,7,23,6
        A2,A,1,05/15,05/20,+,6,24,4
        A3,A,1,05/13,05/23,+,8,32,4
        E2,W,1,05/16,05/24,-,,,
        F1,A,2,05/12,05/14,+,6,14,3
        G1,E,2,05/13,05/15,+,8,12,1
        H1,J,2,05/13,05/16,+,9,11,3
        I1,Q,2,05/14,05/17,+,7,13,1
        J1,W,2,05/14,05/17,+,7,13,8
        G2,E,2,05/19,05/22,-,,,
        G3,E,2,05/20,05/25,+,8,12,1
        H2,J,2,05/21,05/24,+,6,24,5
        """,
        {"sites": "A,J", "first_refs": "A3,C2", "second_refs": "F1,H2",
         "first_pos": 15, "first_den": 70, "second_pos": 12, "second_den": 50,
         "change_pp": 2.57, "relative_change_pct": 12.0},
    ),
}


def make(split: str) -> tuple[str, dict]:
    title, amendment, roster, records, key = PACKETS[split]
    preamble = block("""
        The monitoring bulletin has gone to copy editing. Supply the verified
        quantitative replacement for its two-round comparison using the archived
        materials below. The draft headline is "The fraction of positive samples
        increased across the network." An earlier slide used the mean of the site
        percentages. The editorial board has asked for its published pooled series.

        Methods card, section 4. The longitudinal indicator uses the same eligible
        sites in both rounds; a site must hold a live certificate in each. For
        each round, sum counts across those sites before taking the ratio. Compare
        round 2 with round 1. Report the difference in percentage points and the
        change relative to round 1 in percent. Retain full precision until the end.

        Records office. A lab signature (signed) dates the analysis; the public
        log date (logged) records when that version became available for the
        bulletin. Apply log entries in order of receipt for each site and round.
        A plus certificate replaces the entire prior record, including a prior
        withdrawal. A minus entry withdraws the whole record. An entry logged
        after the applicable cutoff has no effect on the reconstruction.
    """)
    ledger = "\n".join(line.strip() for line in records.strip().splitlines())
    prompt = (
        f"{title}\n\n{preamble}\n\nSigned editorial amendment. {amendment}\n"
        f"Archive directory of all site codes: {roster}.\n\n"
        "Certificate ledger (all dates month/day in the bulletin year):\n"
        "ref,site,round,signed,logged,action,positive,negative,indeterminate\n"
        f"{ledger}\n\n"
        "Return one flat JSON object. sites is a comma-separated string of the "
        "included site codes in alphabetical order without spaces. first_refs "
        "and second_refs give their certificate references for each round in "
        "that same site order, also comma-separated without spaces. first_pos, "
        "first_den, second_pos and second_den are pooled integer counts. "
        "change_pp and relative_change_pct are signed numbers rounded to the "
        "nearest hundredth. Use these nine keys exactly."
    )
    return prompt, dict(key)
