#compdef al-falak
# Zsh completion for al-falak.
# Install to /usr/share/zsh/vendor-completions/_al-falak
# (Debian: debian/completions/al-falak.zsh).
# Note: --timezone takes an IANA ZoneInfo name, which cannot be completed
# statically, so it intentionally has no completer.

_al-falak() {
    local context state state_descr line
    typeset -A opt_args

    local prayer_methods=(DUBAI EGYPTIAN JAKIM KARACHI KUWAIT MOON_SIGHTING_COMMITTEE MUSLIM_WORLD_LEAGUE NONE NORTH_AMERICA QATAR SINGAPORE UMM_AL_QURA UOIF)
    local madhabs=(SHAFI HANAFI)
    local hlrules=(MIDDLE_OF_THE_NIGHT SEVENTH_OF_THE_NIGHT TWILIGHT_ANGLE)
    local polar_rules=(NONE NEAREST_LATITUDE NEAREST_DAY MAKKAH)
    local calendars=(tabular uqu mabims)
    local countries=(MY ID BN SG)
    local qibla_methods=(spherical ellipsoidal)

    _arguments -C \
        '(-h --help)'{-h,--help}'[show help message and exit]' \
        '1:subcommand:->subcommand' \
        '*:: :->args' && return

    case $state in
        subcommand)
            _describe -t subcommands 'al-falak subcommand' '(
                prayer:"Print prayer times."
                qibla:"Print Qibla direction."
                sunnah:"Print Sunnah night markers."
                hijri:"Convert a Gregorian date to a Hijri date."
                moon-sighting:"Print crescent visibility scores."
                astro:"Print lunar position and Delta-T."
            )'
            ;;
        args)
            case ${line[1]} in
                prayer)
                    _arguments \
                        '--latitude=[Latitude, -90 to 90]:latitude:' \
                        '--lat=[Latitude, -90 to 90]:latitude:' \
                        '--longitude=[Longitude, -180 to 180]:longitude:' \
                        '--lon=[Longitude, -180 to 180]:longitude:' \
                        '--date=[Calendar date as YYYY-MM-DD (default: today, UTC)]:date:' \
                        "--method=[Calculation method (default: MUSLIM_WORLD_LEAGUE)]:method:($prayer_methods)" \
                        "--madhab=[SHAFI or HANAFI (default: SHAFI)]:madhab:($madhabs)" \
                        "--high-latitude-rule=[High latitude rule]:rule:($hlrules)" \
                        "--polar-rule=[Polar circle rule]:rule:($polar_rules)" \
                        '--fajr-angle=[Override the method'"'"'s Fajr angle]:degrees:' \
                        '--isha-angle=[Override the method'"'"'s Isha angle]:degrees:' \
                        '--isha-interval=[Override the method'"'"'s Isha interval in minutes]:minutes:' \
                        '--imsak-offset=[Minutes before Fajr for Imsak (default: 10)]:minutes:' \
                        '--ishraq-offset=[Minutes after sunrise for Ishraq (default: 15)]:minutes:' \
                        '--dhuha-offset=[Minutes after sunrise for Dhuha window (default: 28)]:minutes:' \
                        '--elevation=[Observer eye height in metres (default: 0.0)]:metres:' \
                        '--ramadan[Umm al-Qura Ramadan mode]' \
                        '--timezone=[IANA timezone name for display]:timezone:' \
                        '--adjust=[Per-prayer minute offset as NAME=MINUTES (repeatable)]:adjustment:' \
                        '--json[Emit one compact JSON object]' \
                        '(-h --help)'{-h,--help}'[show help message and exit]'
                    ;;
                qibla)
                    _arguments \
                        '--latitude=[Latitude, -90 to 90]:latitude:' \
                        '--lat=[Latitude, -90 to 90]:latitude:' \
                        '--longitude=[Longitude, -180 to 180]:longitude:' \
                        '--lon=[Longitude, -180 to 180]:longitude:' \
                        "--method=[Earth model (default: spherical)]:model:($qibla_methods)" \
                        '--declination=[Local magnetic declination in degrees]:degrees:' \
                        '--json[Emit one compact JSON object]' \
                        '(-h --help)'{-h,--help}'[show help message and exit]'
                    ;;
                sunnah)
                    _arguments \
                        '--latitude=[Latitude, -90 to 90]:latitude:' \
                        '--lat=[Latitude, -90 to 90]:latitude:' \
                        '--longitude=[Longitude, -180 to 180]:longitude:' \
                        '--lon=[Longitude, -180 to 180]:longitude:' \
                        '--date=[Calendar date as YYYY-MM-DD (default: today, UTC)]:date:' \
                        "--method=[Calculation method (default: MUSLIM_WORLD_LEAGUE)]:method:($prayer_methods)" \
                        "--madhab=[SHAFI or HANAFI (default: SHAFI)]:madhab:($madhabs)" \
                        "--high-latitude-rule=[High latitude rule]:rule:($hlrules)" \
                        "--polar-rule=[Polar circle rule]:rule:($polar_rules)" \
                        '--fajr-angle=[Override the method'"'"'s Fajr angle]:degrees:' \
                        '--isha-angle=[Override the method'"'"'s Isha angle]:degrees:' \
                        '--isha-interval=[Override the method'"'"'s Isha interval in minutes]:minutes:' \
                        '--imsak-offset=[Minutes before Fajr for Imsak (default: 10)]:minutes:' \
                        '--ishraq-offset=[Minutes after sunrise for Ishraq (default: 15)]:minutes:' \
                        '--dhuha-offset=[Minutes after sunrise for Dhuha window (default: 28)]:minutes:' \
                        '--elevation=[Observer eye height in metres (default: 0.0)]:metres:' \
                        '--ramadan[Umm al-Qura Ramadan mode]' \
                        '--timezone=[IANA timezone name for display]:timezone:' \
                        '--adjust=[Per-prayer minute offset as NAME=MINUTES (repeatable)]:adjustment:' \
                        '--fraction=[Night fraction in the open interval (0, 1)]:fraction:' \
                        '--start=[Custom night-start anchor as ISO datetime with offset]:datetime:' \
                        '--end=[Custom night-end anchor as ISO datetime with offset]:datetime:' \
                        '--json[Emit one compact JSON object]' \
                        '(-h --help)'{-h,--help}'[show help message and exit]'
                    ;;
                hijri)
                    _arguments \
                        '--date=[Gregorian date as YYYY-MM-DD (default: today, UTC)]:date:' \
                        "--calendar=[Hijri calendar rule]:rule:($calendars)" \
                        "--country=[MABIMS country]:country:($countries)" \
                        '--adjustment-days=[Tabular day shift in -2..2 (default: 0)]:days:' \
                        '--sunset-transition[Roll the Hijri day over at Maghrib]' \
                        '--lat=[Observer latitude for sunset rollover]:latitude:' \
                        '--lon=[Observer longitude for sunset rollover]:longitude:' \
                        '--time=[Wall-clock time as HH:MM[:SS] on --date]:time:' \
                        '--offsets=[JSON offset file]:file:_files' \
                        '--reverse=[Hijri date as YYYY-MM-DD]:hijri-date:' \
                        '--month-length=[Hijri year-month as YYYY-MM]:year-month:' \
                        '--json[Emit one compact JSON object]' \
                        '(-h --help)'{-h,--help}'[show help message and exit]'
                    ;;
                moon-sighting)
                    _arguments \
                        '--latitude=[Latitude, -90 to 90]:latitude:' \
                        '--lat=[Latitude, -90 to 90]:latitude:' \
                        '--longitude=[Longitude, -180 to 180]:longitude:' \
                        '--lon=[Longitude, -180 to 180]:longitude:' \
                        '--date=[Crescent evening as YYYY-MM-DD (required)]:date:' \
                        '--delta-t-override=[Delta-T override in seconds]:seconds:' \
                        '--json[Emit one compact JSON object]' \
                        '(-h --help)'{-h,--help}'[show help message and exit]'
                    ;;
                astro)
                    _arguments -C \
                        '(-h --help)'{-h,--help}'[show help message and exit]' \
                        '1:astro leaf:->astro-leaf' \
                        '*:: :->astro-args' && return
                    case $state in
                        astro-leaf)
                            _describe -t astro-leaves 'astro leaf' '(
                                lunar-position:"Print geocentric Moon position for a Julian Day (TT)."
                                delta-t:"Print Delta-T (TT minus UT1) in seconds for a decimal year."
                            )'
                            ;;
                        astro-args)
                            case ${line[1]} in
                                lunar-position)
                                    _arguments \
                                        '--julian-day=[Julian Day in Terrestrial Time]:julian-day:' \
                                        '--json[Emit one compact JSON object]' \
                                        '(-h --help)'{-h,--help}'[show help message and exit]'
                                    ;;
                                delta-t)
                                    _arguments \
                                        '--year=[Decimal year]:year:' \
                                        '--override=[Delta-T override in seconds]:seconds:' \
                                        '--json[Emit one compact JSON object]' \
                                        '(-h --help)'{-h,--help}'[show help message and exit]'
                                    ;;
                            esac
                            ;;
                    esac
                    ;;
            esac
            ;;
    esac
}

_al-falak "$@"
