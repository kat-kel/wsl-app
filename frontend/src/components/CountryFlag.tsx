type CountryFlagProps = {
    countryCode: string;
};

export function CountryFlag({ countryCode }: CountryFlagProps) {
    return (
        <span
            className={`fi fi-${countryCode.toLowerCase()}`}
            role="img"
            aria-label={countryCode}
        />
    );
}
