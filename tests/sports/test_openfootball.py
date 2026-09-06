from ovigia_dados.sports.openfootball import assess_rondonia_coverage, current_brazil_files


def test_current_brazil_files_detects_only_available_competitions():
    filenames = ["2026_br1.txt", "2025_br2.txt", "2025_brcup.txt", "README.md"]

    assert current_brazil_files(filenames, 2026) == {"serie_a": "2026_br1.txt"}


def test_rondonia_quality_is_insufficient_when_open_data_has_no_local_teams():
    summary, teams = assess_rondonia_coverage(
        season=2026,
        filenames=["2026_br1.txt", "2025_br2.txt", "2025_brcup.txt"],
        clubs_text="Flamengo RJ\nPalmeiras SP\nClube do Remo",
        current_match_texts={"serie_a": "CR Flamengo v Clube do Remo 2-0"},
        monitored_teams=["Porto Velho", "Ji-Paraná", "Genus"],
    )

    assert summary["available_competitions"] == "serie_a"
    assert summary["missing_competitions"] == "copa_do_brasil;serie_b;serie_c;serie_d"
    assert summary["teams_in_club_registry"] == 0
    assert summary["teams_in_current_brazil_matches"] == 0
    assert summary["local_coverage"] == "insufficient_for_rondonia"
    assert all(not row["in_club_registry"] for row in teams)
    assert all(not row["in_current_brazil_matches"] for row in teams)


def test_team_mentions_make_open_data_usable_when_coverage_arrives():
    summary, teams = assess_rondonia_coverage(
        season=2027,
        filenames=["2027_br4.txt"],
        clubs_text="Porto Velho EC, Porto Velho",
        current_match_texts={"serie_d": "Porto Velho v Gama 1-0"},
        monitored_teams=["Porto Velho"],
    )

    assert summary["teams_in_club_registry"] == 1
    assert summary["teams_in_current_brazil_matches"] == 1
    assert summary["local_coverage"] == "usable"
    assert teams == [
        {
            "team_name": "Porto Velho",
            "in_club_registry": True,
            "in_current_brazil_matches": True,
        }
    ]
