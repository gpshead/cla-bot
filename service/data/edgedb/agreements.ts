import e from "../../../dbschema/edgeql";

import {EdgeDBRepository} from "./base";
import {injectable} from "inversify";
import {
  AgreementsRepository,
  AgreementListItem,
  AgreementText,
  RepositoryAgreementInfo,
  Agreement,
  AgreementVersion,
  AgreementTextInput,
} from "../../domain/agreements";

@injectable()
export class EdgeDBAgreementsRepository
  extends EdgeDBRepository
  implements AgreementsRepository
{
  async getAgreement(agreementId: string): Promise<Agreement | null> {
    return await this.run(async (connection) =>
      e
        .select(e.Agreement, (agreement) => ({
          id: true,
          name: true,
          description: true,
          creationTime: agreement.creation_time,
          versions: (version) => ({
            id: true,
            current: true,
            draft: true,
            creationTime: version.creation_time,
            order: version.current,
          }),

          filter: e.op(agreement.id, "=", e.uuid(agreementId)),
        }))
        .run(connection)
    );
  }

  async getAgreementVersion(
    versionId: string
  ): Promise<AgreementVersion | null> {
    return await this.run(async (connection) =>
      e
        .select(e.AgreementVersion, (version) => ({
          id: true,
          current: true,
          draft: true,
          creationTime: version.creation_time,
          agreementId: version["<versions[IS default::Agreement]"].id,
          texts: (text) => ({
            id: true,
            text: true,
            title: true,
            culture: true,
            updateTime: text.update_time,
            creationTime: text.creation_time,
          }),

          filter: e.op(version.id, "=", e.uuid(versionId)),
        }))
        .run(connection)
    );
  }

  async updateAgreement(
    id: string,
    name: string,
    description: string
  ): Promise<void> {
    await this.run(async (connection) =>
      e
        .update(e.Agreement, (agreement) => ({
          filter: e.op(agreement.id, "=", e.uuid(id)),
          set: {
            name,
            description,
            update_time: e.datetime_current(),
          },
        }))
        .run(connection)
    );
  }

  async updateAgreementText(
    id: string,
    title: string,
    body: string
  ): Promise<void> {
    await this.run(async (connection) =>
      e
        .update(e.AgreementText, (text) => ({
          filter: e.op(text.id, "=", e.uuid(id)),
          set: {
            title,
            text: body,
            update_time: e.datetime_current(),
          },
        }))
        .run(connection)
    );
  }

  async updateAgreementVersion(id: string, draft: boolean): Promise<void> {
    await this.run(async (connection) =>
      e
        .update(e.AgreementVersion, (ver) => ({
          filter: e.op(ver.id, "=", e.uuid(id)),
          set: {
            draft,
          },
        }))
        .run(connection)
    );
  }

  async getCurrentAgreementVersionForRepository(
    repositoryFullName: string
  ): Promise<RepositoryAgreementInfo | null> {
    const Version = e
      .select(e.AgreementVersion)
      .filter((v) => {
        const ver = v["<versions[IS default::Agreement]"];
        const repo = ver["<agreement[IS default::Repository]"];

        return e.op(
          e.op(v.current, "and", e.op(v.texts.culture, "=", "en")),
          "and",
          e.op(repo.full_name, "=", repositoryFullName)
        );
      })
      .$assertSingle();

    return await this.run(async (connection) =>
      e
        .select(Version, (v) => ({
          versionId: v.id,
        }))
        .run(connection)
    );
  }

  async getAgreementTextForRepository(
    repositoryFullName: string,
    cultureCode: string
  ): Promise<AgreementText | null> {
    const Text = e
      .select(e.AgreementText)
      .filter((text) => {
        const ver = text["<texts[IS default::AgreementVersion]"];
        const agr = ver["<versions[IS default::Agreement]"];
        const repo = agr["<agreement[IS default::Repository]"];

        return e.op(
          e.op(e.op(text.culture, "=", cultureCode), "and", ver.current),
          "and",
          e.op(repo.full_name, "=", repositoryFullName)
        );
      })
      .$assertSingle();

    return await this.run(async (connection) =>
      e
        .select(Text, (text) => ({
          id: true,
          title: true,
          text: true,
          culture: true,
          versionId: text["<texts[IS default::AgreementVersion]"].id,
          updateTime: text.update_time,
          creationTime: text.creation_time,
        }))
        .run(connection)
    );
  }

  async getAgreementText(
    versionId: string,
    cultureCode: string
  ): Promise<AgreementText | null> {
    const Text = e
      .select(e.AgreementText)
      .filter((text) => {
        const ver = text["<texts[IS default::AgreementVersion]"];

        return e.op(
          e.op(text.culture, "=", cultureCode),
          "and",
          e.op(ver.id, "=", e.uuid(versionId))
        );
      })
      .$assertSingle();

    return await this.run(async (connection) =>
      e
        .select(Text, (text) => ({
          id: true,
          title: true,
          text: true,
          culture: true,
          versionId: text["<texts[IS default::AgreementVersion]"].id,
          updateTime: text.update_time,
          creationTime: text.creation_time,
        }))
        .run(connection)
    );
  }

  async getAgreements(): Promise<AgreementListItem[]> {
    return await this.run(async (connection) =>
      e
        .select(e.Agreement, (agreement) => ({
          id: true,
          name: true,
          description: true,
          creationTime: agreement.creation_time,
        }))
        .run(connection)
    );
  }

  async getCompleteAgreements(): Promise<AgreementListItem[]> {
    return await this.run(async (connection) =>
      e
        .select(e.Agreement, (agreement) => ({
          id: true,
          name: true,
          description: true,
          creationTime: agreement.creation_time,
        }))
        .filter((agreement) => agreement.versions.current)
        .run(connection)
    );
  }

  async createAgreement(
    name: string,
    description?: string
  ): Promise<AgreementListItem> {
    // For best UX, a new agreement is created with a starting
    // version and English text

    return await this.run(async (connection) => {
      const NewAgreement = e.insert(e.Agreement, {
        name,
        description,
        creation_time: e.datetime_current(),
        update_time: e.datetime_current(),
        versions: e.insert(e.AgreementVersion, {
          current: false,
          draft: true,
          creation_time: e.datetime_current(),
          texts: e.insert(e.AgreementText, {
            title: name,
            text: "# Your markdown text here",
            culture: "en",
            creation_time: e.datetime_current(),
            update_time: e.datetime_current(),
          }),
        }),
      });

      return e
        .select(NewAgreement, (agreement) => ({
          id: true,
          name: true,
          description: true,
          creationTime: agreement.creation_time,
        }))
        .run(connection);
    });
  }

  async setCurrentAgreementVersion(
    agreementId: string,
    versionId: string
  ): Promise<void> {
    await this.run(async (connection) => {
      e.update(e.AgreementVersion, (ver) => ({
        filter: e.op(
          ver["<versions[IS default::Agreement]"].id,
          "=",
          e.uuid(agreementId)
        ),
        set: {
          current: e.op(ver.id, "=", e.uuid(versionId)),
        },
      })).run(connection);
    });
  }

  async createAgreementVersion(
    agreementId: string,
    texts: AgreementTextInput[]
  ): Promise<AgreementVersion> {
    //
    // TODO: implement support for more than one text;
    // This is not necessary for now, because the application supports only
    // English language.

    const {title, text, culture} = texts[0];

    return await this.run(async (connection) => {
      const Version = e.insert(e.AgreementVersion, {
        current: false,
        draft: true,
        creation_time: e.datetime_current(),
        texts: e.insert(e.AgreementText, {
          title,
          text,
          culture,
          creation_time: e.datetime_current(),
          update_time: e.datetime_current(),
        }),
      });

      const Update = e.update(e.Agreement, (agreement) => ({
        filter: e.op(agreement.id, "=", e.uuid(agreementId)),
        set: {
          versions: {
            "+=": Version,
          },
        },
      }));

      return e.with(
        [Version, Update],
        e.select(Version, (version) => ({
          id: true,
          current: true,
          draft: true,
          creationTime: version.creation_time,
          agreementId: version["<versions[IS default::Agreement]"].id,
          texts: (text) => ({
            id: true,
            text: true,
            title: true,
            culture: true,
            updateTime: text.update_time,
            creationTime: text.creation_time,
          }),
        }))
      ).run(connection);
    });
  }
}
