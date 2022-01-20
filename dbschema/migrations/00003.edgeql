CREATE MIGRATION m1pzs4o6eiutnftenrfj7zvuxadbvc2jueqkvxnecypg2nokkorhya
    ONTO m1oybewgybopqrrclvjd7yuk2c5wldtkrgh2s7bne72y63hq3joqxq
{
  ALTER TYPE default::Agreement {
      ALTER LINK versions {
          CREATE CONSTRAINT std::exclusive;
      };
      ALTER LINK versions {
          RESET OPTIONALITY;
      };
  };
  ALTER TYPE default::ContributorLicenseAgreement {
      CREATE INDEX ON (.email);
  };
};
