CREATE MIGRATION m152bqefpzrfmkm7j6jdvnmnsclu4xb22siit4nlx2wb2ox6ne4h4q
    ONTO m1pzs4o6eiutnftenrfj7zvuxadbvc2jueqkvxnecypg2nokkorhya
{
  ALTER TYPE default::AgreementVersion {
      ALTER LINK texts {
          CREATE CONSTRAINT std::exclusive;
      };
      ALTER LINK texts {
          RESET OPTIONALITY;
      };
  };
};
