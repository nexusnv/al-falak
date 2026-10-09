# Bash completion for al-falak.
# Install to /usr/share/bash-completion/completions/al-falak
# (Debian: debian/completions/al-falak.bash) or source from ~/.bashrc.

_al_falak_subcommands="prayer qibla sunnah hijri moon-sighting astro"
_al_falak_astro_leaves="lunar-position delta-t"

_al_falak_prayer_methods="DUBAI EGYPTIAN JAKIM KARACHI KUWAIT MOON_SIGHTING_COMMITTEE MUSLIM_WORLD_LEAGUE NONE NORTH_AMERICA QATAR SINGAPORE UMM_AL_QURA UOIF"
_al_falak_madhabs="SHAFI HANAFI"
_al_falak_hlrules="MIDDLE_OF_THE_NIGHT SEVENTH_OF_THE_NIGHT TWILIGHT_ANGLE"
_al_falak_polar_rules="NONE NEAREST_LATITUDE NEAREST_DAY MAKKAH"
_al_falak_calendars="tabular uqu mabims"
_al_falak_countries="MY ID BN SG"
_al_falak_qibla_methods="spherical ellipsoidal"

_al_falak() {
    local cur prev words cword
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    words=("${COMP_WORDS[@]}")
    cword=$COMP_CWORD

    local sub=""
    local i w
    for (( i = 1; i < cword; i++ )); do
        w="${words[i]}"
        case "$w" in
            prayer|qibla|sunnah|hijri|moon-sighting|astro)
                sub="$w"
                break
                ;;
        esac
    done

    # First word: complete subcommand names.
    if [[ $cword -eq 1 ]]; then
        COMPREPLY=( $(compgen -W "$_al_falak_subcommands" -- "$cur") )
        return 0
    fi

    # `astro` leaf position: complete the nested leaf names.
    if [[ "$sub" == "astro" ]]; then
        local leaf=""
        for (( i = 2; i < cword; i++ )); do
            w="${words[i]}"
            case "$w" in
                lunar-position|delta-t)
                    leaf="$w"
                    break
                    ;;
            esac
        done
        if [[ -z "$leaf" && "$prev" == "astro" ]]; then
            COMPREPLY=( $(compgen -W "$_al_falak_astro_leaves" -- "$cur") )
            return 0
        fi
        if [[ -z "$leaf" ]]; then
            COMPREPLY=( $(compgen -W "$_al_falak_astro_leaves" -- "$cur") )
            return 0
        fi
        sub="astro $leaf"
    fi

    # Flag values.
    case "$prev" in
        --method)
            if [[ "$sub" == "qibla" ]]; then
                COMPREPLY=( $(compgen -W "$_al_falak_qibla_methods" -- "$cur") )
            else
                COMPREPLY=( $(compgen -W "$_al_falak_prayer_methods" -- "$cur") )
            fi
            return 0
            ;;
        --madhab)
            COMPREPLY=( $(compgen -W "$_al_falak_madhabs" -- "$cur") )
            return 0
            ;;
        --high-latitude-rule)
            COMPREPLY=( $(compgen -W "$_al_falak_hlrules" -- "$cur") )
            return 0
            ;;
        --polar-rule)
            COMPREPLY=( $(compgen -W "$_al_falak_polar_rules" -- "$cur") )
            return 0
            ;;
        --calendar)
            COMPREPLY=( $(compgen -W "$_al_falak_calendars" -- "$cur") )
            return 0
            ;;
        --country)
            COMPREPLY=( $(compgen -W "$_al_falak_countries" -- "$cur") )
            return 0
            ;;
        --offsets)
            mapfile -t COMPREPLY < <(compgen -f -- "$cur")
            return 0
            ;;
    esac

    # Flag names per subcommand (plus -h/--help everywhere).
    local flags=""
    case "$sub" in
        prayer)
            flags="--latitude --lat --longitude --lon --date --method --madhab --high-latitude-rule --polar-rule --fajr-angle --isha-angle --isha-interval --imsak-offset --ishraq-offset --dhuha-offset --elevation --ramadan --timezone --adjust --json -h --help"
            ;;
        qibla)
            flags="--latitude --lat --longitude --lon --method --declination --json -h --help"
            ;;
        sunnah)
            flags="--latitude --lat --longitude --lon --date --method --madhab --high-latitude-rule --polar-rule --fajr-angle --isha-angle --isha-interval --imsak-offset --ishraq-offset --dhuha-offset --elevation --ramadan --timezone --adjust --fraction --start --end --json -h --help"
            ;;
        hijri)
            flags="--date --calendar --country --adjustment-days --sunset-transition --lat --lon --time --offsets --reverse --month-length --json -h --help"
            ;;
        moon-sighting)
            flags="--latitude --lat --longitude --lon --date --delta-t-override --json -h --help"
            ;;
        "astro lunar-position")
            flags="--julian-day --json -h --help"
            ;;
        "astro delta-t")
            flags="--year --override --json -h --help"
            ;;
        *)
            flags="-h --help"
            ;;
    esac

    if [[ "$cur" == -* ]]; then
        COMPREPLY=( $(compgen -W "$flags" -- "$cur") )
        return 0
    fi
    return 0
}

complete -F _al_falak al-falak
